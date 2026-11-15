from urllib.error import URLError
from app import accessibility
from app.routers import places
import hashlib
import json

def test_dataset_snapshot_matches_pinned_manifest():
    manifest = json.loads((accessibility.ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest["revision"]) == 40
    for name, details in manifest["files"].items():
        assert hashlib.sha256((accessibility.ROOT / name).read_bytes()).hexdigest() == details["sha256"]
    assert (accessibility.ROOT / "NOTICE.md").exists()

def test_station_search_works_without_provider_credentials(env, monkeypatch):
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)
    result = env.client.get("/places/search", params={"q": "Seoul", "kind": "stations"})
    assert result.status_code == 200
    assert result.json()["places"]
    assert all(place["directoryOnly"] and not place["accessibility"] for place in result.json()["places"])
    assert result.json()["generalSearch"] == "not-requested"

def test_missing_credentials_are_not_reported_as_no_results(env, monkeypatch):
    monkeypatch.delenv("KAKAO_REST_API_KEY", raising=False)
    result = env.client.get("/places/search", params={"q": "unlikely-venue-xyz-123"}).json()
    assert result["status"] == "unavailable"
    assert result["generalSearch"] == "not-configured"
    assert result["places"] == []

def test_provider_error_does_not_expose_credentials(env, monkeypatch):
    monkeypatch.setenv("KAKAO_REST_API_KEY", "secret-test-key")
    def fail(*args, **kwargs):
        raise URLError("secret-test-key provider diagnostic")
    monkeypatch.setattr(places, "urlopen", fail)
    response = env.client.get("/places/search", params={"q": "unlikely-venue-xyz-123"})
    assert response.status_code == 503
    assert "secret-test-key" not in response.text

def test_coordinate_validation_and_coverage(env):
    assert env.client.get("/places/search?lat=37").status_code == 400
    assert env.client.get("/accessibility/nearby?lat=999&lng=127").status_code == 400
    result = env.client.get("/accessibility/nearby?lat=35.1&lng=129.1").json()
    assert result["groups"][0]["status"] == "outside-coverage"
    assert all(group["source"]["license"] and group["source"]["date"] for group in result["groups"])

def test_nearby_records_are_bounded_and_tactile_bit_is_distinct_from_crossing():
    row = next(row for row in accessibility.load("osm-walk-nodes.json")["nodes"] if row[3] & 8)
    result = accessibility.nearby("tactile", row[1], row[2], radius=50)
    assert any(item["id"] == f"tactile:{row[0]}" for item in result["items"])
    assert all(item["distanceM"] <= 50 for item in result["items"])
    crossing_only = next(row for row in accessibility.load("osm-walk-nodes.json")["nodes"] if row[3] == 1)
    assert str(crossing_only[0]) not in {item[0] for item in accessibility.records("tactile")}

def test_feature_search_requires_an_anchor_instead_of_inventing_location(env):
    response = env.client.get("/places/search", params={"kind": "tactile"}).json()
    assert response["status"] == "needs-location"
    assert response["places"] == []
    named_station = env.client.get("/places/search", params={"kind": "stations", "q": "성수역"}).json()
    assert named_station["places"]

def test_station_voice_guides_are_marked_as_approximate():
    identifiers = [record[0] for record in accessibility.records("voice_guides")]
    assert len(identifiers) == len(set(identifiers))
    record = accessibility.records("voice_guides")[0]
    result = accessibility.nearby("voice_guides", record[1], record[2], radius=100)
    assert result["items"][0]["coordinatePrecision"] == "station"
