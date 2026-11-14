"""Alembic environment; DATABASE_URL stays outside committed configuration."""
from alembic import context
from app import config
from app.db import Base, make_engine
from app import models  # registers metadata


def run(connection):
    context.configure(connection=connection, target_metadata=Base.metadata,
                      compare_type=True, render_as_batch=connection.dialect.name == 'sqlite')
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    context.configure(url=config.DATABASE_URL, target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    connection = context.config.attributes.get('connection')
    if connection is not None:
        run(connection)
    else:
        engine = make_engine(config.DATABASE_URL)
        try:
            with engine.begin() as connection:
                run(connection)
        finally:
            engine.dispose()
