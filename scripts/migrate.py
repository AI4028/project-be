"""Upgrade the database; optionally adopt an existing, verified baseline schema."""
import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db import Base, engine, make_engine
from sqlalchemy import MetaData
from app import models


def migrate(bind, adopt_existing=False):
    cfg = Config(str(Path(__file__).resolve().parent.parent / 'alembic.ini'))
    with bind.begin() as connection:
        cfg.attributes['connection'] = connection
        current = MigrationContext.configure(connection).get_current_revision()
        if adopt_existing and current is None:
            # Compare against the immutable baseline, not future application models.
            baseline_engine = make_engine('sqlite:///:memory:')
            baseline = MetaData()
            try:
                with baseline_engine.begin() as temporary:
                    cfg.attributes['connection'] = temporary
                    command.upgrade(cfg, '0001')
                    baseline.reflect(temporary)
                    baseline.remove(baseline.tables['alembic_version'])
            finally:
                baseline_engine.dispose()
                cfg.attributes['connection'] = connection
            differences = compare_metadata(MigrationContext.configure(connection), baseline)
            if differences:
                raise ValueError('Existing schema differs from application models; review it before adopting.')
            command.stamp(cfg, '0001')
        command.upgrade(cfg, 'head')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adopt-existing', action='store_true')
    args = parser.parse_args()
    migrate(engine, args.adopt_existing)
