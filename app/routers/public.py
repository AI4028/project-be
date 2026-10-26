"""Open endpoints: store info for Stage 1 (accessibility) and menus."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.errors import AppError
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
    }
    if with_menu:
        data["menu"] = sorted(store.menu or [], key=lambda m: m.get("sortOrder", 0))
    return data


@router.get("/stores")
def list_stores(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    """All stores with location and accessibility info (no menus)."""
    return [store_dict(s, with_menu=False) for s in db.scalars(select(Store).order_by(Store.name))]


@router.get("/stores/{store_id}")
def get_store(store_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """One store with its full menu."""
    store = db.get(Store, store_id)
    if store is None:
        raise AppError("store-not-found", "Store not found.")
    return store_dict(store, with_menu=True)


@router.get("/kiosks/{kiosk_id}")
def get_kiosk(kiosk_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Public kiosk info, e.g. its name to read out before connecting."""
    kiosk = db.get(Kiosk, kiosk_id)
    if kiosk is None:
        raise AppError("kiosk-not-found", "Kiosk not found.")
    return {"kioskId": kiosk.id, "storeId": kiosk.store_id, "name": kiosk.name, "nameEn": kiosk.name_en}
