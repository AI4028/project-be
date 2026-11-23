"""TMAP pedestrian summaries for the bounded nearby venue list."""
import json
import os
from concurrent.futures import ThreadPoolExecutor, wait
from http.client import HTTPException
from urllib.request import Request, urlopen

_workers = ThreadPoolExecutor(max_workers=8)


def _pedestrian_route(key, lat, lng, destination):
    end_lat, end_lng = destination
    body = {
        "startX": lng, "startY": lat, "endX": end_lng, "endY": end_lat,
        "startName": "Origin", "endName": "Cafe", "reqCoordType": "WGS84GEO",
        "resCoordType": "WGS84GEO", "searchOption": "10",
    }
    request = Request("https://apis.openapi.sk.com/tmap/routes/pedestrian?version=1",
                      data=json.dumps(body).encode(),
                      headers={"appKey": key, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urlopen(request, timeout=2.5) as response:
            totals = json.load(response)["features"][0]["properties"]
        meters, seconds = totals["totalDistance"], totals["totalTime"]
        if all(type(value) is int and value >= 0 for value in (meters, seconds)):
            return {"distanceM": meters, "durationS": seconds}
    except (OSError, HTTPException, ValueError, IndexError, TypeError, KeyError):
        pass
    return None


def add_walking_routes(venues, lat, lng):
    key = os.environ.get("TMAP_APP_KEY")
    destinations = {}
    for venue in venues:
        venue["walkingRoute"] = None
        location = venue.get("location")
        if key and location:
            point = (location["lat"], location["lng"])
            destinations.setdefault(point, []).append(venue)
    if not destinations:
        return

    jobs = {_workers.submit(_pedestrian_route, key, lat, lng, point): matches
            for point, matches in destinations.items()}
    # Leave time for Kakao discovery within the web client's 12-second deadline.
    finished, pending = wait(jobs, timeout=4)
    for job in pending:
        job.cancel()
    for job in finished:
        route = job.result()
        for venue in jobs[job]:
            venue["walkingRoute"] = route
