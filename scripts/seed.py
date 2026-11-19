"""Load a store, its menu and kiosks from JSON.

    python -m scripts.seed seed/gist-cafe.json

Re-running replaces the store and menu and renames kiosks; keys, sessions and orders are kept.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.config import MEDIA_DIR
from app.db import SessionLocal, create_tables
from app.models import Kiosk, Store


def check_image(url: Any, owner: str) -> None:
    """Photos are files under media/ ("/media/...") or full https URLs."""
    if url is None:
        return
    if not isinstance(url, str) or not (url.startswith("/media/") or url.startswith("https://")):
        raise ValueError(f'{owner}: imageUrl must start with "/media/" or "https://".')
    if url.startswith("/media/") and not (MEDIA_DIR.parent / url.lstrip("/")).is_file():
        raise ValueError(f"{owner}: photo file not found: {url}")


def load_store(db: Session, data: dict[str, Any]) -> tuple[str, int, int]:
    store_id = data.get("storeId")
    info = data.get("store")
    if not store_id or not info:
        raise ValueError('The JSON file needs "storeId" and "store".')
    menu = data.get("menu", [])
    kiosks = data.get("kiosks", [])

    seen: set[str] = set()
    for item in menu:
        if not item.get("id") or item["id"] in seen:
            raise ValueError(f"Menu item id missing or duplicated: {item.get('id')}")
        seen.add(item["id"])
        if not isinstance(item.get("price"), int) or item["price"] < 0:
            raise ValueError(f"{item['id']}: price must be a whole number of won.")
        check_image(item.get("imageUrl"), item["id"])
    check_image(info.get("imageUrl"), store_id)
    phone = info.get("phone")
    if phone is not None and not re.fullmatch(r"\+?[0-9][0-9-]{6,18}", phone):
        raise ValueError(f"{store_id}: phone must be digits and dashes, e.g. 062-715-0000.")
    for k in kiosks:
        if not re.fullmatch(r"[A-Z0-9]{4}", k.get("kioskId", "")):
            raise ValueError(f"Kiosk ID {k.get('kioskId')!r} must be 4 characters, A-Z and 0-9.")

    location = info.get("location") or {}
    store = db.get(Store, store_id) or Store(id=store_id)
    store.name = info["name"]
    store.name_en = info.get("nameEn")
    store.address = info.get("address")
    store.lat = location.get("lat")
    store.lng = location.get("lng")
    store.geofence_radius_m = info.get("geofenceRadiusM")
    store.ordering_methods = info.get("orderingMethods", [])
    store.accessibility = info.get("accessibility", {})
    store.kiosk_features = info.get("kioskFeatures", {})
    store.indoor_directions = info.get("indoorDirections")
    store.pickup_location = info.get("pickupLocation")
    store.image_url = info.get("imageUrl")
    store.phone = info.get("phone")
    store.hours = info.get("hours")
    store.hours_en = info.get("hoursEn")
    store.menu = menu
    db.add(store)
    db.flush()

    for k in kiosks:
        kiosk = db.get(Kiosk, k["kioskId"]) or Kiosk(id=k["kioskId"])
        kiosk.store_id = store_id
        kiosk.name = k.get("name")
        kiosk.name_en = k.get("nameEn")
        db.add(kiosk)

    db.commit()
    return store_id, len(menu), len(kiosks)


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m scripts.seed <store.json>")
    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    create_tables()
    with SessionLocal() as db:
        store_id, n_menu, n_kiosks = load_store(db, data)
    print(f"Seeded {store_id}: {n_menu} menu items, {n_kiosks} kiosk(s).")


if __name__ == "__main__":
    main()
