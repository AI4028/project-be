from app import config, service
from app.models import Kiosk, KioskSession
from tests.test_api import new_phone, connect
from sqlalchemy.exc import OperationalError


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
