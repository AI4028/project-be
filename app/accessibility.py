"""Read-only nearby public records. A record is not a verified accessible route."""
from __future__ import annotations
import json
import math
from functools import lru_cache
from pathlib import Path
from app.logic import distance_m

ROOT = Path(__file__).parent / "data" / "accessibility"
SOURCES = {
    "audio_signals": {"name": "Seoul Open Data · OA-15543", "url": "https://data.seoul.go.kr/dataList/OA-15543/S/1/datasetView.do", "license": "KOGL Type 1", "date": "2026-05-28", "coverage": "Seoul"},
    "voice_guides": {"name": "Seoul Metro · OA-22526", "url": "https://data.seoul.go.kr/dataList/OA-22526/S/1/datasetView.do", "license": "KOGL Type 1", "date": "2025-08", "coverage": "Seoul Metro lines 1–8; station-level coordinates"},
    "crossings": {"name": "Korean public crosswalk standard data · 15028201", "url": "https://www.data.go.kr/data/15028201/standard.do", "license": "Public data; unrestricted use as recorded by source", "date": "2026-08-23", "coverage": "South Korea; incomplete records"},
    "tactile": {"name": "© OpenStreetMap contributors", "url": "https://www.openstreetmap.org/copyright", "license": "ODbL 1.0", "date": "2026-08-16", "coverage": "South Korea; mapped nodes only"},
    "stations": {"name": "Korea National Railway · 15013205", "url": "https://www.data.go.kr/data/15013205/standard.do", "license": "Public data; source-specific terms", "date": "2026-08-17", "coverage": "South Korea"},
}

@lru_cache(maxsize=8)
def load(name):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))

def in_korea(lat, lng):
    # Coarse service bounds, not a territorial boundary claim.
    return 33 <= lat <= 39 and 124 <= lng <= 132

def in_seoul(lat, lng):
    return 37.41 <= lat <= 37.72 and 126.76 <= lng <= 127.19

def station_places(query, lat=None, lng=None):
    q = query.strip().casefold().replace(" ", "").removesuffix("역")
    found = []
    for station in load("subway-stations.json"):
        names = f"{station['name']} {station.get('nameEn', '')} {station.get('roadAddress', '')}".casefold().replace(" ", "")
        if q and q not in names:
            continue
        if not q and lat is None:
            continue
        distance = round(distance_m(lat, lng, station["lat"], station["lng"])) if lat is not None else None
        if not q and distance > 5000:
            continue
        found.append({"storeId": f"station:{station['stationId']}:{station['lineName']}", "name": f"{station['name']} · {station['lineName']}",
            "nameEn": f"{station['nameEn']} · {station['lineName']}" if station.get("nameEn") else None, "address": station.get("roadAddress", ""),
            "location": {"lat": station["lat"], "lng": station["lng"]}, "accessibility": {}, "directoryOnly": True,
            "placeKind": "station", "source": SOURCES["stations"], "distanceM": distance})
    if lat is not None:
        found.sort(key=lambda item: item["distanceM"])
    return found[:15]

@lru_cache(maxsize=4)
def records(kind):
    if kind == "audio_signals":
        return [(str(index), row[0], row[1], None) for index, row in enumerate(load("audio-signals.json")["signals"])]
    if kind == "crossings":
        return [(str(index), row[0], row[1], None) for index, row in enumerate(load("crosswalks.json")["crosswalks"])]
    if kind == "tactile":
        # Upstream bit 3 is the tactile_paving=yes flag, not the crossing bit.
        return [(str(row[0]), row[1], row[2], None) for row in load("osm-walk-nodes.json")["nodes"] if row[3] & 8]
    if kind == "voice_guides":
        by_name = {}
        for entry in load("voice-guides.json")["entries"]:
            by_name.setdefault(entry["key"], []).append(f"{entry['line']} · {entry['location']}")
        return [(f"{s['stationId']}:{s['lineName']}", s["lat"], s["lng"], s["name"] + ": " + "; ".join(by_name[s["name"].removesuffix("역")][:3]))
            for s in load("subway-stations.json") if in_seoul(s["lat"], s["lng"]) and s["name"].removesuffix("역") in by_name]
    return []

def nearby(kind, lat, lng, radius=300, limit=5):
    source = SOURCES[kind]
    if not in_korea(lat, lng) or (kind in ("audio_signals", "voice_guides") and not in_seoul(lat, lng)):
        return {"kind": kind, "status": "outside-coverage", "source": source, "items": []}
    items = []
    lat_span = radius / 110000
    lng_span = radius / (110000 * math.cos(math.radians(lat)))
    for identifier, y, x, detail in records(kind):
        if abs(lat - y) > lat_span or abs(lng - x) > lng_span:
            continue
        meters = distance_m(lat, lng, y, x)
        if meters <= radius:
            items.append({"id": f"{kind}:{identifier}", "location": {"lat": y, "lng": x},
                "distanceM": round(meters), "detail": detail, "coordinatePrecision": "station" if kind == "voice_guides" else "recorded-point"})
    items.sort(key=lambda item: item["distanceM"])
    return {"kind": kind, "status": "records" if items else "not-recorded", "source": source, "items": items[:limit]}

def feature_places(kind, lat, lng, radius=1000):
    result = nearby(kind, lat, lng, radius, 15)
    return [{"storeId": item["id"], "name": kind, "address": item["detail"] or result["source"]["name"],
        "location": item["location"], "distanceM": item["distanceM"], "accessibility": {}, "directoryOnly": True,
        "placeKind": kind, "source": result["source"]} for item in result["items"]], result["status"]
