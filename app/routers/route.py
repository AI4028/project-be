"""Walking routes from 길동무 (Gildongmu, MIT, https://github.com/Engccer/gildongmu).

Gildongmu's public API needs no key but sends no CORS headers, so the web app
can't call it directly. This proxy also trims the answer to what the phone uses
and caches it briefly, because Gildongmu limits requests per caller IP.
"""
from __future__ import annotations

import json
import os
import time
from collections import OrderedDict
from threading import Lock
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, Query

from app.accessibility import in_korea
from app.errors import AppError
from app.limits import RateLimiter

router = APIRouter(tags=["route"])

GILDONGMU_URL = "https://gildongmu.dodoplanet.space"
SOURCE = {"name": "길동무", "url": GILDONGMU_URL, "license": "MIT"}
CACHE_SECONDS = 60
CACHE_SIZE = 200
route_limit = RateLimiter(6)

_cache: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()
_cache_lock = Lock()


def _cached(key):
    with _cache_lock:
        entry = _cache.get(key)
        if entry and time.monotonic() - entry[0] < CACHE_SECONDS:
            return entry[1]
        _cache.pop(key, None)
        return None


def _remember(key, value):
    with _cache_lock:
        _cache[key] = (time.monotonic(), value)
        _cache.move_to_end(key)
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)


def _point(raw):
    return {"lat": float(raw["lat"]), "lng": float(raw["lng"])}


def _step(raw):
    parts = raw.get("parts") or {}
    return {
        "instruction": str(raw.get("description") or ""),
        "turn": parts.get("turn") or None,
        "action": raw.get("action") or None,
        "distanceM": round(float(raw.get("distanceMeters") or 0)),
        "path": [_point(p) for p in raw.get("pathCoords") or []],
    }


def fetch_walk(origin, dest, lang, accessible):
    params = {
        "origin": f"{origin[0]},{origin[1]}",
        "dest": f"{dest[0]},{dest[1]}",
        "lang": lang,
        "includeGeometry": "1",
        "wording": "2",
    }
    if accessible:
        params["accessible"] = "true"
    base = os.environ.get("GILDONGMU_API_URL", GILDONGMU_URL).rstrip("/")
    request = Request(f"{base}/api/route/walk?" + urlencode(params), headers={"User-Agent": "Galjido/1.0"})
    try:
        with urlopen(request, timeout=8) as response:
            payload = json.load(response)
    except HTTPError as error:
        if error.code == 429:
            raise AppError("route-busy", "Route service is busy; retry shortly.") from None
        raise AppError("route-unavailable", "Walking routes are temporarily unavailable.") from None
    except (URLError, TimeoutError, ValueError):
        raise AppError("route-unavailable", "Walking routes are temporarily unavailable.") from None
    if payload.get("outOfCoverage"):
        return {"status": "outside-coverage", "steps": [], "source": SOURCE}
    result = payload.get("result")
    try:
        steps = [_step(step) for step in result["steps"]]
        return {
            "status": "ok",
            "distanceM": round(float(result["distanceMeters"])),
            "durationS": round(float(result.get("durationSeconds") or 0)),
            "steps": steps,
            "source": SOURCE,
        }
    except (TypeError, KeyError, ValueError):
        return {"status": "no-route", "steps": [], "source": SOURCE}


@router.get("/route/walk", dependencies=[Depends(route_limit)])
def walk_route(
    originLat: float = Query(ge=-90, le=90),
    originLng: float = Query(ge=-180, le=180),
    destLat: float = Query(ge=-90, le=90),
    destLng: float = Query(ge=-180, le=180),
    lang: Literal["ko", "en"] = "ko",
    accessible: bool = False,
):
    if not (in_korea(originLat, originLng) and in_korea(destLat, destLng)):
        return {"status": "outside-coverage", "steps": [], "source": SOURCE}
    # About 10 m: a customer standing still reuses the answer instead of spending
    # the shared upstream quota.
    origin = (round(originLat, 4), round(originLng, 4))
    dest = (round(destLat, 5), round(destLng, 5))
    key = (origin, dest, lang, accessible)
    cached = _cached(key)
    if cached is not None:
        return cached
    route = fetch_walk(origin, dest, lang, accessible)
    if route["status"] == "ok":
        _remember(key, route)
    return route
