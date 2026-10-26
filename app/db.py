"""Database connection (SQLAlchemy 2.0).

SQLite locally, PostgreSQL in production; the code is the same for both.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app import config


class Base(DeclarativeBase):
    pass


def make_engine(url: str, **kwargs) -> Engine:
    if url.startswith("sqlite"):
        kwargs.setdefault("connect_args", {"check_same_thread": False, "timeout": 15})
        engine = create_engine(url, **kwargs)

        # SQLite: start every transaction with BEGIN IMMEDIATE so requests run
        # one at a time and never read data another request is changing.
        @event.listens_for(engine, "connect")
        def _no_autobegin(dbapi_conn, _record):
            dbapi_conn.isolation_level = None

        @event.listens_for(engine, "begin")
        def _begin_immediate(conn):
            conn.exec_driver_sql("BEGIN IMMEDIATE")

        return engine
    return create_engine(url, pool_pre_ping=True, **kwargs)


engine = make_engine(config.DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one database session per request."""
    with SessionLocal() as db:
        yield db


def create_tables(bind: Engine | None = None) -> None:
    from app import models  # noqa: F401  (registers the tables)

    Base.metadata.create_all(bind or engine)
