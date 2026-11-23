"""Public place search shared by native and web. Credentials stay on the server."""
from __future__ import annotations
import json
import os
from itertools import islice
from typing import Literal
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.accessibility import station_places, feature_places, nearby, in_korea
from app.db import get_db
from app.errors import AppError
from app.models import Store
from app.walking_routes import add_walking_routes
from app.routers.public import nearby_stores, store_dict

router = APIRouter(tags=["places"])


def _search_text(value: str | None) -> str:
    return "".join((value or "").casefold().split())


def registered_places(db: Session, query: str, lat: float | None, lng: float | None):
    if not query.strip():
        return nearby_stores(lat, lng, radius_m=5000, db=db)[:15] if lat is not None and lng is not None else []

    search = _search_text(query)
    results = (
        store_dict(store, with_menu=False)
        for store in db.scalars(select(Store).order_by(Store.name, Store.id))
        if any(search in _search_text(value) for value in (store.name, store.name_en, store.address, store.address_en))
        or any(
            search in _search_text(item.get(field))
            for item in (store.menu or [])
            for field in ("name", "nameEn")
        )
    )
    return list(islice(results, 15))

def kakao_search(query, lat=None, lng=None):
    key = os.environ.get("KAKAO_REST_API_KEY")
    if not key:
        return None
    endpoint = "keyword" if query else "category"
    params = {"query": query, "size": 15} if query else {"category_group_code": "CE7", "radius": 2000, "size": 15}
    if lat is not None:
        params.update(x=lng, y=lat, sort="distance")
    request = Request(f"https://dapi.kakao.com/v2/local/search/{endpoint}.json?" + urlencode(params),
        headers={"Authorization": f"KakaoAK {key}", "User-Agent": "Galjido/1.0"})
    try:
        with urlopen(request, timeout=6) as response:
            payload = json.load(response)
        result = []
        for item in payload["documents"]:
            y, x = float(item["y"]), float(item["x"])
            if not (-90 <= y <= 90 and -180 <= x <= 180):
                continue
            result.append({"storeId": "place:" + str(item["id"]), "name": item["place_name"],
                "address": item.get("road_address_name") or item.get("address_name", ""),
                "location": {"lat": y, "lng": x}, "accessibility": {}, "directoryOnly": True,
                "placeKind": "venue", "source": {"name": "Kakao Local", "url": "https://map.kakao.com", "license": "Provider terms", "coverage": "South Korea", "date": "live"}})
        return result
    except (URLError, HTTPError, ValueError, KeyError, TypeError):
        raise AppError("places-unavailable", "Place search is temporarily unavailable.") from None

@router.get("/places/search")
def search_places(q: str = Query("", max_length=100),
    kind: Literal["all", "stations", "audio_signals", "voice_guides", "tactile", "crossings"] = "all",
    lat: float | None = Query(None, ge=-90, le=90), lng: float | None = Query(None, ge=-180, le=180),
    db: Session = Depends(get_db)):
    if (lat is None) != (lng is None):
        raise AppError("bad-request", "Provide both latitude and longitude.")
    if lat is not None and not in_korea(lat, lng):
        if not q.strip() or kind not in ("all", "stations"):
            return {"places": [], "status": "outside-coverage", "generalSearch": "unavailable"}
        # A named destination can be searched before arriving in Korea.
        lat = lng = None
    stations = station_places(q, lat, lng)
    if kind not in ("all", "stations"):
        if lat is None and stations:
            lat, lng = stations[0]["location"]["lat"], stations[0]["location"]["lng"]
        if lat is None:
            return {"places": [], "status": "needs-location", "generalSearch": "not-requested"}
        places, status = feature_places(kind, lat, lng)
        return {"places": places, "status": status, "generalSearch": "not-requested"}
    if kind == "stations" or (not q.strip() and lat is None):
        return {"places": stations, "status": "results" if stations else "empty", "generalSearch": "not-requested"}
    provider_error = None
    try:
        venues = kakao_search(q.strip(), lat, lng)
        capability = "available" if venues is not None else "not-configured"
    except AppError as error:
        venues, capability = [], "unavailable"
        provider_error = error
    cafes = [*registered_places(db, q, lat, lng), *(venues or [])]
    if not q.strip() and lat is not None:
        add_walking_routes(cafes, lat, lng)
        cafes.sort(key=lambda cafe: cafe["walkingRoute"]["distanceM"] if cafe["walkingRoute"] else float("inf"))
    places = [*cafes, *stations]
    if provider_error and not places:
        raise provider_error
    return {"places": places, "status": "results" if places else "empty" if q.strip() or capability == "available" else "unavailable", "generalSearch": capability}

@router.get("/accessibility/nearby")
def nearby_accessibility(lat: float = Query(ge=-90, le=90), lng: float = Query(ge=-180, le=180), radiusM: int = Query(300, ge=25, le=1000)):
    return {"radiusM": radiusM, "groups": [nearby(kind, lat, lng, radiusM) for kind in ("audio_signals", "voice_guides", "tactile", "crossings")]}
