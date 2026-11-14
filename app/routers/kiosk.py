"""Kiosk endpoints. Auth: `Bearer ksk_...`."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app.responses import AvailabilityOut, Ended, HelpEvent, OrderEvent, OrderOut, SessionOut, TokenOut
from app import service
from app.auth import current_kiosk
from app.clock import get_now
from app.db import get_db
from app.models import Kiosk
from app.realtime import hub
from app.schemas import AvailabilityIn, StatusIn
from app.responses import KioskState
from app.routers.public import get_store

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


@router.get("/state", response_model=KioskState, response_model_exclude_unset=True)
def kiosk_state(kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db),
                now: int = Depends(get_now)):
    """Restore the screen after reconnecting, including missed stock changes."""
    return {"session": service.kiosk_active_session(db, kiosk, now),
            "orders": service.kiosk_orders(db, kiosk, now),
            "store": get_store(kiosk.store_id, db)}


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
    result = service.set_item_availability(db, kiosk, item_id, body.available)
    background.add_task(hub.send, f"store:{kiosk.store_id}",
                        {"type": "availability", "storeId": kiosk.store_id, **result})
    return result
