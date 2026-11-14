from app import config, service
from app.models import Kiosk, KioskSession
from tests.test_api import new_phone, connect


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
