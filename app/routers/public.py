"""Public endpoints: stores, accessibility info, menus."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.responses import KioskOut, StoreOut
from app.db import get_db
from app.errors import AppError
from app.logic import distance_m
from app.models import Kiosk, Store

router = APIRouter(tags=["stores"])


def store_dict(store: Store, with_menu: bool) -> dict[str, Any]:
    data: dict[str, Any] = {
        "storeId": store.id,
        "name": store.name,
        "nameEn": store.name_en,
        "address": store.address,
        "location": {"lat": store.lat, "lng": store.lng} if store.lat is not None else None,
        "geofenceRadiusM": store.geofence_radius_m,
        "orderingMethods": store.ordering_methods or [],
        "accessibility": store.accessibility or {},
        "kioskFeatures": store.kiosk_features or {},
        "indoorDirections": store.indoor_directions,
        "pickupLocation": store.pickup_location,
        "imageUrl": store.image_url,
        "phone": store.phone,
        "hours": store.hours,
        "hoursEn": store.hours_en,
        "hasOrderTerminal": bool(store.has_order_terminal),
        "orderingPaused": bool(store.ordering_paused),
    }
    if with_menu:
        data["menu"] = sorted(store.menu or [], key=lambda m: m.get("sortOrder", 0))
    return data


@router.get("/stores", response_model=list[StoreOut], response_model_exclude_unset=True)
def list_stores(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """Store summaries and short, localized suggestions for discovery."""
    stores = []
    for store in db.scalars(select(Store).order_by(Store.name)):
        summary = store_dict(store, with_menu=False)
        summary["menuSuggestions"] = [
            {field: item[field] for field in ("name", "nameEn") if item.get(field)}
            for item in sorted(store.menu or [], key=lambda item: item.get("sortOrder", 0))
            if item.get("available", True) and item.get("name")
        ][:5]
        stores.append(summary)
    return stores


@router.get("/stores/nearby", response_model=list[StoreOut], response_model_exclude_unset=True)
def nearby_stores(
    lat: float = Query(ge=-90, le=90),
    lng: float = Query(ge=-180, le=180),
    radius_m: int = Query(2000, alias="radiusM", ge=1, le=20000),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Stores within radiusM, nearest first, with `distanceM` and `insideGeofence`."""
    found = []
    for store in db.scalars(select(Store).where(Store.lat.is_not(None), Store.lng.is_not(None))):
        meters = distance_m(lat, lng, store.lat, store.lng)
        if meters <= radius_m:
            data = store_dict(store, with_menu=False)
            data["distanceM"] = round(meters)
            data["insideGeofence"] = store.geofence_radius_m is not None and meters <= store.geofence_radius_m
            found.append(data)
    return sorted(found, key=lambda s: s["distanceM"])


@router.get("/stores/{store_id}", response_model=StoreOut, response_model_exclude_unset=True)
def get_store(store_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """One store with its full menu."""
    store = db.get(Store, store_id)
    if store is None:
        raise AppError("store-not-found", "Store not found.")
    return store_dict(store, with_menu=True)


@router.get("/kiosks/{kiosk_id}", response_model=KioskOut, response_model_exclude_unset=True)
def get_kiosk(kiosk_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Kiosk name, e.g. to read aloud before pairing."""
    kiosk = db.get(Kiosk, kiosk_id)
    if kiosk is None:
        raise AppError("kiosk-not-found", "Kiosk not found.")
    return {"kioskId": kiosk.id, "storeId": kiosk.store_id, "name": kiosk.name, "nameEn": kiosk.name_en}
