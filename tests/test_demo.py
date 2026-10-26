"""Demo shortcuts (app/routers/demo.py): off by default, usable with DEMO_MODE."""

from __future__ import annotations

import pytest
from starlette.websockets import WebSocketDisconnect

from app import config
from app.models import Kiosk
from tests.test_api import error, new_phone


@pytest.fixture
def demo(monkeypatch):
    monkeypatch.setattr(config, "DEMO_MODE", True)


def test_demo_routes_are_off_by_default(env):
    error(env.client.get("/kiosks/GK01/token"), 404, "demo-disabled")
    error(env.client.post("/proximity", json={"distance": 1.0}), 404, "demo-disabled")
    with pytest.raises(WebSocketDisconnect) as closed:
        with env.client.websocket_connect("/ws/proximity") as ws:
            ws.receive_json()
    assert closed.value.code == 4404


def test_demo_token_lets_a_phone_connect(env, demo):
    res = env.client.get("/kiosks/GK01/token")
    assert res.status_code == 200, res.text
    token = res.json()["token"]

    res = env.client.post("/sessions", json={"kioskId": "GK01", "token": token}, headers=new_phone(env))
    assert res.status_code == 201, res.text

    # Asking again within the refresh window returns the same token.
    assert env.client.get("/kiosks/GK01/token").json()["token"] == token


def test_demo_token_does_not_mark_the_kiosk_as_seen(env, demo):
    env.client.get("/kiosks/GK01/token")
    with env.db() as db:
        assert db.get(Kiosk, "GK01").last_seen_at is None


def test_demo_token_for_unknown_kiosk(env, demo):
    error(env.client.get("/kiosks/ZZ99/token"), 404, "kiosk-not-found")


def test_proximity_is_forwarded_with_rssi(env, demo):
    with env.client.websocket_connect("/ws/proximity") as ws:
        res = env.client.post("/proximity", json={"distance": 2.5, "storeName": "GIST Cafe점", "kioskId": "GK01", "rssi": -68})
        assert res.status_code == 200, res.text
        assert ws.receive_json() == {
            "type": "proximity",
            "distance": 2.5,
            "storeName": "GIST Cafe점",
            "kioskId": "GK01",
            "rssi": -68,
        }
