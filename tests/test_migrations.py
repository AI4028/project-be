from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
import pytest
from sqlalchemy import text
from app.db import Base, make_engine, create_tables
from scripts.migrate import migrate


def test_fresh_database_migrates_to_current_models(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path / "fresh.db"}')
    try:
        migrate(engine)
        migrate(engine)
        with engine.connect() as connection:
            assert compare_metadata(MigrationContext.configure(connection), Base.metadata) == []
            assert MigrationContext.configure(connection).get_current_revision() == '0002'
    finally:
        engine.dispose()


def test_adoption_preserves_existing_data_and_rejects_wrong_schema(tmp_path):
    engine = make_engine(f'sqlite:///{tmp_path / "existing.db"}')
    try:
        from alembic import command
        from alembic.config import Config
        with engine.begin() as connection:
            cfg = Config('alembic.ini')
            cfg.attributes['connection'] = connection
            command.upgrade(cfg, '0001')
            connection.execute(text('DROP TABLE alembic_version'))
        with engine.begin() as connection:
            connection.execute(text("INSERT INTO devices (id, token_hash, created_at) VALUES ('test', 'hash', 1)"))
        migrate(engine, adopt_existing=True)
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT token_hash FROM devices WHERE id='test'")) == 'hash'
    finally:
        engine.dispose()
    engine = make_engine(f'sqlite:///{tmp_path / "wrong.db"}')
    try:
        with pytest.raises(ValueError, match='differs'):
            migrate(engine, adopt_existing=True)
    finally:
        engine.dispose()
