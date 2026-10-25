"""End-to-end tests through the real HTTP and WebSocket endpoints."""

from __future__ import annotations

import pytest
from starlette.websockets import WebSocketDisconnect

from app import config

AMERICANO = [{"itemId": "americano", "qty": 1, "options": {"temp": "ice", "size": "large"}}]


# ---------- helpers ----------


def new_phone(env) -> dict[str, str]:
    res = env.client.post("/devices")
    assert res.status_code == 201
    return {"Authorization": f"Bearer {res.json()['token']}"}


def heartbeat(env) -> str:
    res = env.client.post("/kiosk/heartbeat", headers=env.kiosk)
    assert res.status_code == 200, res.text
    return res.json()["token"]


def connect(env, phone, token=None, kiosk_id="GK01"):
    return env.client.post("/sessions", json={"kioskId": kiosk_id, "token": token or heartbeat(env)}, headers=phone)


def connected(env):
    phone = new_phone(env)
    res = connect(env, phone)
    assert res.status_code == 201, res.text
    return phone, res.json()["sessionId"]


def error(res, status: int, code: str) -> None:
    assert res.status_code == status, res.text
    assert res.json()["error"] == code, res.text


# ---------- tests ----------


def test_full_flow_with_live_updates(env):
    phone = new_phone(env)
    with env.client.websocket_connect(f"/ws/kiosk?token={env.kiosk_key}") as kiosk_ws:
        res = connect(env, phone)
        assert res.status_code == 201
        conn = res.json()
        assert conn["type"] == "connected"
        assert conn["kioskName"] == "키오스크 1"
        assert conn["storeName"] == "GIST 카페 (데모)"
        assert kiosk_ws.receive_json()["type"] == "connected"
        session_id = conn["sessionId"]

        token = phone["Authorization"].split()[1]
        with env.client.websocket_connect(f"/ws/sessions/{session_id}?token={token}") as phone_ws:
            res = env.client.put(f"/sessions/{session_id}/cart", json={"items": AMERICANO}, headers=phone)
            assert res.json()["total"] == 3000
            live = kiosk_ws.receive_json()
            assert live["type"] == "cart" and live["summary"] == "아메리카노 (아이스, 라지) 1개"
            assert phone_ws.receive_json()["type"] == "cart"

            res = env.client.post(f"/sessions/{session_id}/order", json={"items": AMERICANO}, headers=phone)
            assert res.status_code == 201
            order = res.json()
            assert (order["orderNumber"], order["total"], order["status"]) == (1, 3000, "submitted")
            assert kiosk_ws.receive_json()["type"] == "ordered"
            assert phone_ws.receive_json()["type"] == "ordered"

            for status in ["accepted", "preparing", "ready"]:
                env.clock.advance(1000)
                res = env.client.post(f"/kiosk/orders/{order['orderId']}/status", json={"status": status}, headers=env.kiosk)
                assert res.status_code == 200
                update = phone_ws.receive_json()
                assert (update["type"], update["status"]) == ("order_status", status)
                kiosk_ws.receive_json()

    mine = env.client.get(f"/orders/{order['orderId']}", headers=phone).json()
    assert mine["status"] == "ready"
    assert mine["lines"][0]["name"] == "아메리카노"
    error(env.client.get(f"/orders/{order['orderId']}", headers=new_phone(env)), 404, "order-not-found")

    queue = env.client.get("/kiosk/orders", headers=env.kiosk).json()
    assert [o["orderNumber"] for o in queue] == [1]
    assert env.client.get("/kiosk/session", headers=env.kiosk).json() is None, "kiosk is free after the order"


def test_order_numbers_count_up_and_restart_each_korean_day(env):
    numbers = []
    for advance in [0, 60_000, 13 * 60 * 60_000]:  # 11:00, 11:01, then next day 00:01 KST
        env.clock.advance(advance)
        phone, session_id = connected(env)
        res = env.client.post(f"/sessions/{session_id}/order", json={"items": AMERICANO}, headers=phone)
        numbers.append(res.json()["orderNumber"])
    assert numbers == [1, 2, 1]


def test_wrong_or_expired_bluetooth_token_cannot_connect(env):
    phone = new_phone(env)
    token = heartbeat(env)
    error(connect(env, phone, "ZZZZZZZZ"), 403, "token-invalid")
    env.clock.advance(config.TOKEN_TTL_MS + 1)
    error(connect(env, phone, token), 403, "token-invalid")
    error(connect(env, phone, token, kiosk_id="gk01"), 400, "bad-kiosk-id")
    error(connect(env, phone, "short"), 400, "bad-token")
    error(connect(env, phone, token, kiosk_id="NONE"), 404, "kiosk-not-found")


def test_token_rotates_every_30s_and_previous_still_works(env):
    first = heartbeat(env)
    env.clock.advance(10_000)
    assert heartbeat(env) == first, "no rotation within 30 s"
    env.clock.advance(config.TOKEN_REFRESH_MS)
    assert heartbeat(env) != first
    assert connect(env, new_phone(env), first).status_code == 201


def test_one_phone_per_kiosk_reconnect_and_idle_takeover(env):
    alice, session_id = connected(env)
    token = heartbeat(env)
    bob = new_phone(env)
    error(connect(env, bob, token), 409, "kiosk-busy")
    assert connect(env, alice, token).json()["sessionId"] == session_id, "same phone gets the same session"

    env.clock.advance(config.SESSION_IDLE_MS + 1)
    res = connect(env, bob)
    assert res.status_code == 201 and res.json()["sessionId"] != session_id
    assert env.client.get(f"/sessions/{session_id}", headers=alice).json()["status"] == "expired"
    error(env.client.post(f"/sessions/{session_id}/order", json={"items": AMERICANO}, headers=alice), 409, "session-expired")


def test_help_request_and_staff_resolves_it(env):
    phone, session_id = connected(env)
    assert env.client.post(f"/sessions/{session_id}/help", headers=phone).json()["type"] == "help"
    assert env.client.get("/kiosk/session", headers=env.kiosk).json()["helpRequested"] is True
    error(env.client.post(f"/kiosk/sessions/{session_id}/resolve-help", headers=env.other_kiosk), 404, "session-not-found")
    assert env.client.post(f"/kiosk/sessions/{session_id}/resolve-help", headers=env.kiosk).json()["type"] == "help_resolved"
    assert env.client.get(f"/sessions/{session_id}", headers=phone).json()["helpRequested"] is False


def test_either_side_can_end_the_session(env):
    phone, session_id = connected(env)
    error(env.client.post(f"/sessions/{session_id}/end", headers=new_phone(env)), 403, "not-your-session")
    assert env.client.post(f"/kiosk/sessions/{session_id}/end", headers=env.kiosk).json()["status"] == "ended"
    assert env.client.get("/kiosk/session", headers=env.kiosk).json() is None
    error(env.client.put(f"/sessions/{session_id}/cart", json={"items": []}, headers=phone), 409, "session-expired")

    phone2, session2 = connected(env)
    assert env.client.post(f"/sessions/{session2}/end", headers=phone2).json()["status"] == "ended"


def test_cancel_only_before_staff_accepts_and_stores_are_separate(env):
    phone, session_id = connected(env)
    order_id = env.client.post(f"/sessions/{session_id}/order", json={"items": AMERICANO}, headers=phone).json()["orderId"]
    error(env.client.post(f"/orders/{order_id}/cancel", headers=new_phone(env)), 404, "order-not-found")
    error(
        env.client.post(f"/kiosk/orders/{order_id}/status", json={"status": "accepted"}, headers=env.other_kiosk),
        404,
        "order-not-found",
    )
    assert env.client.get("/kiosk/orders", headers=env.other_kiosk).json() == []
    assert env.client.post(f"/orders/{order_id}/cancel", headers=phone).json()["status"] == "cancelled"
    error(env.client.post(f"/kiosk/orders/{order_id}/status", json={"status": "accepted"}, headers=env.kiosk), 409, "bad-transition")

    phone2, session2 = connected(env)
    order2 = env.client.post(f"/sessions/{session2}/order", json={"items": AMERICANO}, headers=phone2).json()["orderId"]
    env.client.post(f"/kiosk/orders/{order2}/status", json={"status": "accepted"}, headers=env.kiosk)
    error(env.client.post(f"/orders/{order2}/cancel", headers=phone2), 409, "too-late-to-cancel")


def test_roles_and_tokens_are_enforced(env):
    phone, session_id = connected(env)
    error(env.client.post("/kiosk/heartbeat", headers=phone), 401, "not-kiosk")
    error(env.client.post("/sessions", json={"kioskId": "GK01", "token": heartbeat(env)}, headers=env.kiosk), 401, "not-signed-in")
    error(env.client.post("/sessions", json={"kioskId": "GK01", "token": heartbeat(env)}), 401, "not-signed-in")
    error(env.client.post("/kiosk/heartbeat", headers={"Authorization": "Bearer ksk_made_up"}), 401, "not-kiosk")
    error(env.client.post(f"/sessions/{session_id}/order", json={"items": AMERICANO}, headers=new_phone(env)), 403, "not-your-session")


def test_request_problems_return_clear_errors(env):
    phone, session_id = connected(env)
    url = f"/sessions/{session_id}/order"
    error(env.client.post(url, json={"items": AMERICANO, "paymentMethod": "bitcoin"}, headers=phone), 400, "bad-payment-method")
    error(env.client.post(url, json={}, headers=phone), 400, "bad-request")
    error(env.client.post(url, json={"items": [{"itemId": "americano", "qty": 1}]}, headers=phone), 400, "missing-option")
    error(env.client.post(url, json={"items": [{"itemId": "cheesecake", "qty": 1}]}, headers=phone), 409, "item-unavailable")


def test_staff_can_mark_items_sold_out(env):
    phone, session_id = connected(env)
    res = env.client.put("/kiosk/menu/americano/availability", json={"available": False}, headers=env.kiosk)
    assert res.json() == {"itemId": "americano", "available": False}
    menu = {m["id"]: m for m in env.client.get("/stores/gist-cafe").json()["menu"]}
    assert menu["americano"]["available"] is False
    error(env.client.put(f"/sessions/{session_id}/cart", json={"items": AMERICANO}, headers=phone), 409, "item-unavailable")
    env.client.put("/kiosk/menu/americano/availability", json={"available": True}, headers=env.kiosk)
    assert env.client.put(f"/sessions/{session_id}/cart", json={"items": AMERICANO}, headers=phone).status_code == 200
    error(env.client.put("/kiosk/menu/nope/availability", json={"available": False}, headers=env.kiosk), 404, "unknown-item")


def test_store_info_for_accessibility_and_menus(env):
    stores = {s["storeId"]: s for s in env.client.get("/stores").json()}
    gist = stores["gist-cafe"]
    assert "menu" not in gist
    assert gist["location"] == {"lat": 35.2286, "lng": 126.8436}
    assert gist["orderingMethods"] == ["kiosk", "phone", "staff"]
    assert "stepFreeEntrance" in gist["accessibility"]
    menu = env.client.get("/stores/gist-cafe").json()["menu"]
    assert [m["id"] for m in menu][:2] == ["americano", "cafe-latte"]
    error(env.client.get("/stores/nope"), 404, "store-not-found")
    assert env.client.get("/kiosks/GK01").json()["name"] == "키오스크 1"


def test_live_update_connections_check_who_is_listening(env):
    phone, session_id = connected(env)
    for url, code in [
        ("/ws/kiosk?token=ksk_wrong", 4401),
        ("/ws/kiosk", 4401),
        (f"/ws/sessions/{session_id}?token=dev_wrong", 4401),
        (f"/ws/sessions/{session_id}?token={new_phone(env)['Authorization'].split()[1]}", 4403),
    ]:
        with pytest.raises(WebSocketDisconnect) as closed:
            with env.client.websocket_connect(url) as ws:
                ws.receive_json()
        assert closed.value.code == code, url


def test_health_endpoints_still_work(env):
    assert env.client.get("/").json() == {"message": "Project backend is running"}
    assert env.client.get("/health").json() == {"status": "ok"}
