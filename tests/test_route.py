import json
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse

import pytest

from app.routers import route

GIST = {"destLat": 35.229, "destLng": 126.8436}
NEARBY = {"originLat": 35.2255, "originLng": 126.8405, **GIST}

# Trimmed from a real /api/route/walk answer near GIST.
WALK = {
    "result": {
        "distanceMeters": 571,
        "durationSeconds": 513,
        "steps": [
            {
                "description": "496m 이동",
                "distanceMeters": 496,
                "pathCoords": [{"lat": 35.2255, "lng": 126.8405}, {"lat": 35.2293, "lng": 126.8429}],
            },
            {
                "description": "오른쪽으로 도세요. 그 후 75m 이동",
                "distanceMeters": 75,
                "action": "right",
                "parts": {"turn": "오른쪽으로 도세요", "body": "75m 이동"},
                "pathCoords": [{"lat": 35.2293, "lng": 126.8429}, {"lat": 35.229, "lng": 126.8436}],
            },
        ],
        "kind": "broad",
    }
}


@pytest.fixture(autouse=True)
def fresh_cache():
    route._cache.clear()
    route.route_limit.entries.clear()


def answer(payload, requests):
    def respond(request, timeout):
        requests.append(request)
        return BytesIO(json.dumps(payload).encode())
    return respond


def test_walk_route_is_trimmed_and_cached(env, monkeypatch):
    requests = []
    monkeypatch.setattr(route, "urlopen", answer(WALK, requests))
    body = env.client.get("/route/walk", params=NEARBY).json()
    assert body["status"] == "ok"
    assert body["distanceM"] == 571 and body["durationS"] == 513
    assert body["steps"][1] == {
        "instruction": "오른쪽으로 도세요. 그 후 75m 이동",
        "turn": "오른쪽으로 도세요",
        "action": "right",
        "distanceM": 75,
        "path": [{"lat": 35.2293, "lng": 126.8429}, {"lat": 35.229, "lng": 126.8436}],
    }
    assert body["source"]["name"] == "길동무"
    query = parse_qs(urlparse(requests[0].full_url).query)
    assert query["origin"] == ["35.2255,126.8405"] and query["dest"] == ["35.229,126.8436"]
    assert query["includeGeometry"] == ["1"] and query["lang"] == ["ko"]
    assert "accessible" not in query
    # A few metres away: same answer, no second upstream call.
    assert env.client.get("/route/walk", params={**NEARBY, "originLat": 35.22552}).json() == body
    assert len(requests) == 1


def test_step_free_route_and_english_are_forwarded(env, monkeypatch):
    requests = []
    monkeypatch.setattr(route, "urlopen", answer(WALK, requests))
    env.client.get("/route/walk", params={**NEARBY, "lang": "en", "accessible": "true"})
    query = parse_qs(urlparse(requests[0].full_url).query)
    assert query["lang"] == ["en"] and query["accessible"] == ["true"]


def test_outside_korea_is_answered_without_calling_upstream(env, monkeypatch):
    def never(*args, **kwargs):
        raise AssertionError("upstream called")
    monkeypatch.setattr(route, "urlopen", never)
    body = env.client.get("/route/walk", params={**NEARBY, "originLat": 51.5, "originLng": -0.12}).json()
    assert body["status"] == "outside-coverage" and body["steps"] == []


def test_upstream_failures_map_to_stable_errors(env, monkeypatch):
    def offline(*args, **kwargs):
        raise URLError("offline")
    monkeypatch.setattr(route, "urlopen", offline)
    response = env.client.get("/route/walk", params=NEARBY)
    assert response.status_code == 503 and response.json()["error"] == "route-unavailable"

    def busy(request, timeout):
        raise HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
    monkeypatch.setattr(route, "urlopen", busy)
    response = env.client.get("/route/walk", params=NEARBY)
    assert response.status_code == 429 and response.json()["error"] == "route-busy"

    monkeypatch.setattr(route, "urlopen", answer({"result": None}, []))
    assert env.client.get("/route/walk", params=NEARBY).json()["status"] == "no-route"


def test_bad_coordinates_are_rejected(env):
    assert env.client.get("/route/walk", params={**NEARBY, "originLat": 95}).status_code == 400
    assert env.client.get("/route/walk", params={"originLat": 35.2}).status_code == 400
