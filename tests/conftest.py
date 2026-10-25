"""Test setup: a fresh SQLite database per test, the demo cafe loaded, a
kiosk key issued, and a clock the tests can move forward."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

import app.db as dbmod
from app.clock import get_now
from app.main import app
from scripts.create_kiosk import issue_kiosk_key
from scripts.seed import load_store

SEED = json.loads((Path(__file__).resolve().parent.parent / "seed" / "gist-cafe.json").read_text(encoding="utf-8"))

# 2026-10-06 11:00 Korea time
T0 = int(datetime(2026, 10, 6, 2, 0, tzinfo=timezone.utc).timestamp() * 1000)

# A second store with its own kiosk, to check stores can't touch each other.
OTHER_STORE = {
    "storeId": "other-cafe",
    "store": {"name": "다른 카페"},
    "kiosks": [{"kioskId": "XK01", "name": "다른 키오스크"}],
    "menu": [{"id": "tea", "name": "녹차", "price": 3000, "available": True, "options": []}],
}


class Clock:
    def __init__(self, now: int) -> None:
        self.now = now

    def advance(self, ms: int) -> int:
        self.now += ms
        return self.now


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = dbmod.make_engine(f"sqlite:///{tmp_path / 'test.db'}")
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(dbmod, "engine", engine)
    monkeypatch.setattr(dbmod, "SessionLocal", session_factory)
    dbmod.create_tables(engine)
    with session_factory() as db:
        load_store(db, SEED)
        load_store(db, OTHER_STORE)
        kiosk_key = issue_kiosk_key(db, "GK01")
        other_key = issue_kiosk_key(db, "XK01")

    clock = Clock(T0)
    app.dependency_overrides[get_now] = lambda: clock.now
    with TestClient(app) as client:
        yield SimpleNamespace(
            client=client,
            clock=clock,
            db=session_factory,
            kiosk={"Authorization": f"Bearer {kiosk_key}"},
            kiosk_key=kiosk_key,
            other_kiosk={"Authorization": f"Bearer {other_key}"},
        )
    app.dependency_overrides.clear()
    engine.dispose()
