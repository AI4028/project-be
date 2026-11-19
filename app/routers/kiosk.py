"""Kiosk endpoints. Auth: `Bearer ksk_...`."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.responses import AvailabilityOut, OrderingOut, Ended, HelpEvent, OrderEvent, OrderOut, SessionOut, TokenOut
from app import config, menu_photos, service
from app.errors import AppError
from app.auth import current_kiosk
from app.clock import get_now
from app.db import get_db
from app.models import Kiosk
from app.realtime import hub
from app.schemas import AvailabilityIn, OrderingIn, StatusIn
from app.responses import KioskState
from app.routers.public import get_store

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


@router.get("/state", response_model=KioskState, response_model_exclude_unset=True)
def kiosk_state(kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db),
                now: int = Depends(get_now)):
    """Restore the screen after reconnecting, including missed stock changes."""
    return {"photoUploadsEnabled": menu_photos.sample_in_bucket("menu/americano.jpg"),
            "session": service.kiosk_active_session(db, kiosk, now),
            "orders": service.kiosk_orders(db, kiosk, now),
            "store": get_store(kiosk.store_id, db),
            "helpRequests": service.kiosk_help_requests(db, kiosk, now)}


@router.post("/heartbeat", response_model=TokenOut, response_model_exclude_unset=True)
def heartbeat(
    kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db), now: int = Depends(get_now)
) -> dict[str, Any]:
    """The Bluetooth pairing token to broadcast. Call again after `refreshInMs`."""
    return service.kiosk_heartbeat(db, kiosk, now)


@router.get("/session", response_model=SessionOut | None, response_model_exclude_unset=True)
def active_session(
    kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db), now: int = Depends(get_now)
) -> dict[str, Any] | None:
    """The connected phone and its cart, or null."""
    return service.kiosk_active_session(db, kiosk, now)


@router.get("/orders", response_model=list[OrderOut], response_model_exclude_unset=True)
def todays_orders(
    status: str | None = None,
    kiosk: Kiosk = Depends(current_kiosk),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> list[dict[str, Any]]:
    """Today's orders, newest first. Filter with ?status=."""
    return service.kiosk_orders(db, kiosk, now, status)


@router.post("/orders/{order_id}/status", response_model=OrderEvent, response_model_exclude_unset=True)
def set_order_status(
    order_id: str,
    body: StatusIn,
    background: BackgroundTasks,
    kiosk: Kiosk = Depends(current_kiosk),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    ev = service.update_order_status(db, kiosk, order_id, body.status, now)
    background.add_task(hub.publish, ev)
    return ev


@router.post("/sessions/{session_id}/resolve-help", response_model=HelpEvent, response_model_exclude_unset=True)
def help_handled(
    session_id: str,
    background: BackgroundTasks,
    kiosk: Kiosk = Depends(current_kiosk),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    ev = service.resolve_help(db, kiosk, session_id, now)
    background.add_task(hub.publish, ev)
    return ev


@router.post("/sessions/{session_id}/end", response_model=Ended, response_model_exclude_unset=True)
def end_phone_session(
    session_id: str,
    background: BackgroundTasks,
    kiosk: Kiosk = Depends(current_kiosk),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    ev = service.end_session(db, kiosk, session_id, now)
    background.add_task(hub.publish, ev)
    return ev


@router.put("/menu/{item_id}/availability", response_model=AvailabilityOut, response_model_exclude_unset=True)
def set_availability(
    item_id: str, body: AvailabilityIn, background: BackgroundTasks, kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Mark an item sold out or back in stock."""
    result = service.update_menu_item(db, kiosk.store_id, item_id, {"available": body.available})
    background.add_task(hub.send, f"store:{kiosk.store_id}",
                        {"type": "availability", "storeId": kiosk.store_id, **result})
    return result


@router.put("/menu/{item_id}/photo")
async def replace_menu_photo(item_id: str, request: Request, kiosk: Kiosk = Depends(current_kiosk),
                             db: Session = Depends(get_db)) -> dict[str, str]:
    """Replace one photo in the authenticated kiosk's store using raw image bytes."""
    if not config.MENU_PHOTO_BUCKET:
        raise AppError("photo-storage-unavailable", "Menu photo storage is not configured.")

    def check_item() -> str:
        store_id = kiosk.store_id
        if not any(item.get("id") == item_id for item in service.store_menu(db, store_id)):
            raise AppError("unknown-item", "Item not on this menu.")
        # Release SQLite's write lock while receiving and uploading the image.
        db.rollback()
        return store_id

    store_id = await run_in_threadpool(check_item)
    raw = bytearray()
    async for chunk in request.stream():
        if len(raw) + len(chunk) > menu_photos.MAX_BYTES:
            raise AppError("photo-too-large", "Choose a photo no larger than 1 MiB.")
        raw.extend(chunk)
    image_url = await run_in_threadpool(menu_photos.save_photo, bytes(raw))
    return await run_in_threadpool(service.update_menu_item, db, store_id, item_id, {"imageUrl": image_url})


@router.put("/ordering", response_model=OrderingOut, response_model_exclude_unset=True)
def set_ordering(
    body: OrderingIn, background: BackgroundTasks, kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Pause or resume phone ordering for this store. Menus stay visible."""
    result = service.set_ordering_paused(db, kiosk, body.paused)
    background.add_task(hub.send, f"store:{kiosk.store_id}", {"type": "ordering", **result})
    return result
