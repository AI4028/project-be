import io
import json

import pytest

from hardware import ble_kiosk_bridge as bridge


def test_authenticated_heartbeat_becomes_a_serial_advertisement(env, monkeypatch):
    def send(request, *, timeout):
        assert request.full_url == "http://localhost:8000/kiosk/heartbeat"
        assert request.get_method() == "POST"
        response = env.client.post("/kiosk/heartbeat", headers=dict(request.header_items()))
        assert response.status_code == 200
        return io.BytesIO(response.content)

    monkeypatch.setattr(bridge, "urlopen", send)
    monkeypatch.setattr(bridge.time, "time_ns", lambda: env.clock.now * 1_000_000)
    port = io.BytesIO()
    assert bridge.update_beacon(port, "http://localhost:8000", env.kiosk_key) == 30
    command, payload, lifetime = port.getvalue().decode("ascii").split()
    assert command == "ADV"
    assert payload.startswith("LKGK01")
    assert int(lifetime) == 59_000
    device = env.client.post("/devices").json()
    response = env.client.post(
        "/sessions",
        headers={"Authorization": f"Bearer {device['token']}"},
        json={"kioskId": payload[2:6], "token": payload[6:]},
    )
    assert response.status_code == 201
    assert response.json()["kioskId"] == "GK01"


@pytest.mark.parametrize("overrides", [
    {"expiresAtMs": 2_000},
    {"expiresAtMs": 62_001},
    {"kioskId": "GK01\n"},
    {"token": "A8UDEFGH"},
    {"refreshInMs": 0},
])
def test_invalid_or_stale_heartbeat_writes_nothing(overrides, monkeypatch):
    heartbeat = {
        "kioskId": "GK01", "token": "ABCDEFGH", "expiresAtMs": 61_000, "refreshInMs": 30_000,
        **overrides,
    }
    monkeypatch.setattr(bridge, "urlopen", lambda *args, **kwargs: io.BytesIO(json.dumps(heartbeat).encode()))
    monkeypatch.setattr(bridge.time, "time_ns", lambda: 1_000_000_000)
    port = io.BytesIO()
    with pytest.raises(ValueError):
        bridge.update_beacon(port, "http://localhost:8000", "example")
    assert port.getvalue() == b""
