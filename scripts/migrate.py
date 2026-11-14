"""Upgrade the database; optionally adopt an existing, verified baseline schema."""
import argparse
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db import Base, engine
from app import models


def migrate(bind, adopt_existing=False):
    cfg = Config(str(Path(__file__).resolve().parent.parent / 'alembic.ini'))
    with bind.begin() as connection:
        cfg.attributes['connection'] = connection
        current = MigrationContext.configure(connection).get_current_revision()
        if adopt_existing and current is None:
            differences = compare_metadata(MigrationContext.configure(connection), Base.metadata)
            if differences:
                raise ValueError('Existing schema differs from application models; review it before adopting.')
            command.stamp(cfg, '0001')
        command.upgrade(cfg, 'head')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--adopt-existing', action='store_true')
    args = parser.parse_args()
    migrate(engine, args.adopt_existing)
