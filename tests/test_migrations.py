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
            assert MigrationContext.configure(connection).get_current_revision() == '0007'
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


def test_menu_photo_upgrade_preserves_store_edits(tmp_path):
    from alembic import command
    from alembic.config import Config
    from sqlalchemy.orm import Session
    from app.models import Store

    engine = make_engine(f'sqlite:///{tmp_path / "menu-photos.db"}')
    menu = [
        {"id": "americano", "price": 7300, "available": False, "options": []},
        {"id": "cafe-latte", "imageUrl": "https://example.com/custom.jpg"},
        {"id": "tea", "name": "House tea"},
    ]
    try:
        with engine.begin() as connection:
            cfg = Config('alembic.ini')
            cfg.attributes['connection'] = connection
            command.upgrade(cfg, '0006')
        with Session(engine) as db:
            db.add(Store(id="existing-cafe", name="Existing cafe", menu=menu))
            db.commit()
        migrate(engine)
        with Session(engine) as db:
            assert db.get(Store, "existing-cafe").menu == [
                {**menu[0], "imageUrl": "/media/menu/americano.jpg"}, *menu[1:],
            ]
    finally:
        engine.dispose()
