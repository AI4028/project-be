from app import config, service
from app.models import Kiosk, KioskSession
from tests.test_api import new_phone, connect
from sqlalchemy.exc import OperationalError
import pytest
from starlette.websockets import WebSocketDisconnect


def test_idle_session_reads_expired_and_cleanup_releases_kiosk_once(env):
    phone = new_phone(env)
    sid = connect(env, phone).json()["sessionId"]
    env.clock.advance(config.SESSION_IDLE_MS - 1)
    assert env.client.get(f"/sessions/{sid}", headers=phone).json()["status"] == "active"
    env.clock.advance(1)
    assert env.client.get(f"/sessions/{sid}", headers=phone).json()["status"] == "expired"
    with env.db() as db:
        events = service.expire_sessions(db, env.clock.now)
        assert len(events) == 1
        assert events[0]["status"] == "expired"
        assert db.get(Kiosk, "GK01").active_session_id is None
        assert db.get(KioskSession, sid).status == "expired"
        assert service.expire_sessions(db, env.clock.now) == []

def test_openapi_describes_order_and_cart_responses(env):
    schema = env.client.get('/openapi.json').json()
    response = schema['paths']['/sessions/{session_id}/order']['post']['responses']['201']
    assert response['content']['application/json']['schema']['$ref'].endswith('/Ordered')
    assert 'orderNumber' in schema['components']['schemas']['Ordered']['properties']
    assert 'unitPrice' in schema['components']['schemas']['LineOut']['properties']
    stores = env.client.get('/stores').json()
    assert 'menu' not in stores[0]


def test_readiness_reports_database_failure_without_details(env, monkeypatch):
    import app.db as database
    assert env.client.get('/ready').status_code == 200
    def unavailable():
        raise OperationalError('secret database address', {}, Exception('password'))
    monkeypatch.setattr(database, 'SessionLocal', unavailable)
    response = env.client.get('/ready')
    assert response.status_code == 503
    assert response.json() == {'status': 'unavailable'}
    assert env.client.get('/health').status_code == 200


def test_registration_throttle_and_window_reset(env, monkeypatch):
    import app.limits as limits
    now = [1000.0]
    monkeypatch.setattr(limits.time, 'monotonic', lambda: now[0])
    monkeypatch.setattr(limits.registration_limit, 'limit', 2)
    assert env.client.post('/devices').status_code == 201
    assert env.client.post('/devices').status_code == 201
    limited = env.client.post('/devices')
    assert limited.status_code == 429
    assert int(limited.headers['Retry-After']) > 0
    now[0] += 61
    assert env.client.post('/devices').status_code == 201


def test_revocation_rejects_token_and_releases_kiosk(env):
    phone = new_phone(env)
    sid = connect(env, phone).json()['sessionId']
    assert env.client.delete('/devices/me', headers=phone).json() == {'status': 'revoked'}
    assert env.client.get(f'/sessions/{sid}', headers=phone).status_code == 401
    assert env.client.get('/kiosk/session', headers=env.kiosk).json() is None
    assert connect(env, new_phone(env)).status_code == 201


def test_reconnect_snapshot_and_live_stock_update(env):
    phone = new_phone(env)
    sid = connect(env, phone).json()['sessionId']
    token = phone['Authorization'].split()[1]
    with env.client.websocket_connect(f'/ws/sessions/{sid}?token={token}') as ws:
        response = env.client.put('/kiosk/menu/americano/availability',
                                  json={'available': False}, headers=env.kiosk)
        assert response.status_code == 200
        event = ws.receive_json()
        assert event == {'type': 'availability', 'storeId': 'gist-cafe',
                         'itemId': 'americano', 'available': False}
    state = env.client.get(f'/sessions/{sid}/state', headers=phone).json()
    assert state['session']['sessionId'] == sid
    assert state['order'] is None
    assert next(item for item in state['store']['menu'] if item['id'] == 'americano')['available'] is False
    assert env.client.get(f'/sessions/{sid}/state', headers=new_phone(env)).status_code == 404
    kiosk_state = env.client.get('/kiosk/state', headers=env.kiosk).json()
    assert kiosk_state['session']['sessionId'] == sid
    assert env.client.get('/kiosk/state', headers=env.other_kiosk).json()['session'] is None


def test_idle_takeover_still_emits_expiry_without_releasing_new_phone(env):
    old_sid = connect(env, new_phone(env)).json()['sessionId']
    env.clock.advance(config.SESSION_IDLE_MS)
    new_sid = connect(env, new_phone(env)).json()['sessionId']
    with env.db() as db:
        events = service.expire_sessions(db, env.clock.now)
        assert [e['sessionId'] for e in events] == [old_sid]
        assert db.get(Kiosk, 'GK01').active_session_id == new_sid


def test_revocation_closes_existing_phone_socket(env):
    phone = new_phone(env)
    sid = connect(env, phone).json()['sessionId']
    token = phone['Authorization'].split()[1]
    with env.client.websocket_connect(f'/ws/sessions/{sid}?token={token}') as ws:
        assert env.client.delete('/devices/me', headers=phone).status_code == 200
        assert ws.receive_json()['type'] == 'ended'
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 4401

def test_order_retry_returns_original_result_and_rejects_conflicting_payload(env):
    from tests.test_api import AMERICANO
    phone = new_phone(env)
    sid = connect(env, phone).json()['sessionId']
    quote = env.client.put(f'/sessions/{sid}/cart', headers=phone, json={'items': AMERICANO}).json()
    body = {'items': AMERICANO, 'quoteId': quote['quoteId']}
    headers = {**phone, 'Idempotency-Key': 'retry-key-123'}
    first = env.client.post(f'/sessions/{sid}/order', headers=headers, json=body)
    assert first.status_code == 201
    retry = env.client.post(f'/sessions/{sid}/order', headers=headers, json=body)
    assert retry.status_code == 201
    assert retry.json() == first.json()
    conflict = env.client.post(f'/sessions/{sid}/order', headers=headers, json={**body, 'note': 'different'})
    assert conflict.status_code == 409
    assert conflict.json()['error'] == 'idempotency-conflict'
    assert len(env.client.get('/kiosk/orders', headers=env.kiosk).json()) == 1


def test_changed_price_requires_new_quote_without_creating_order(env):
    from tests.test_api import AMERICANO
    from app.models import Store
    phone = new_phone(env)
    sid = connect(env, phone).json()['sessionId']
    quote = env.client.put(f'/sessions/{sid}/cart', headers=phone, json={'items': AMERICANO}).json()
    with env.db() as db:
        store = db.get(Store, 'gist-cafe')
        menu = [dict(item) for item in store.menu]
        next(item for item in menu if item['id'] == 'americano')['price'] += 500
        store.menu = menu
        db.commit()
    response = env.client.post(f'/sessions/{sid}/order', headers=phone,
                               json={'items': AMERICANO, 'quoteId': quote['quoteId']})
    assert response.status_code == 409
    assert response.json()['error'] == 'price-changed'
    assert env.client.get('/kiosk/orders', headers=env.kiosk).json() == []
    refreshed = env.client.put(f'/sessions/{sid}/cart', headers=phone, json={'items': AMERICANO}).json()
    assert env.client.post(f'/sessions/{sid}/order', headers=phone,
                           json={'items': AMERICANO, 'quoteId': refreshed['quoteId']}).status_code == 201

def test_concurrent_order_retries_create_one_order(env):
    from concurrent.futures import ThreadPoolExecutor
    from tests.test_api import AMERICANO
    phone = new_phone(env)
    sid = connect(env, phone).json()['sessionId']
    quote = env.client.put(f'/sessions/{sid}/cart', headers=phone, json={'items': AMERICANO}).json()
    def submit():
        return env.client.post(f'/sessions/{sid}/order',
            headers={**phone, 'Idempotency-Key': 'concurrent-retry'},
            json={'items': AMERICANO, 'quoteId': quote['quoteId']})
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: submit(), range(2)))
    assert [r.status_code for r in responses] == [201, 201]
    assert responses[0].json() == responses[1].json()
    assert len(env.client.get('/kiosk/orders', headers=env.kiosk).json()) == 1
