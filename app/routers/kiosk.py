"""Endpoints the kiosk app calls. Send `Authorization: Bearer ksk_...`."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app import service
from app.auth import current_kiosk
from app.clock import get_now
from app.db import get_db
from app.models import Kiosk
from app.realtime import hub
from app.schemas import AvailabilityIn, StatusIn

router = APIRouter(prefix="/kiosk", tags=["kiosk"])


@router.post("/heartbeat")
def heartbeat(kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db), now: int = Depends(get_now)) -> dict[str, Any]:
    """Get the Bluetooth pairing token. Call again after `refreshInMs`."""
    return service.kiosk_heartbeat(db, kiosk, now)


@router.get("/session")
def active_session(
    kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db), now: int = Depends(get_now)
) -> Optional[dict[str, Any]]:
    """The phone currently connected (with its cart), or null."""
    return service.kiosk_active_session(db, kiosk, now)


@router.get("/orders")
def todays_orders(
    status: Optional[str] = None,
    kiosk: Kiosk = Depends(current_kiosk),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> list[dict[str, Any]]:
    """Today's orders for this store, newest first. Optional ?status=submitted"""
    return service.kiosk_orders(db, kiosk, now, status)


@router.post("/orders/{order_id}/status")
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


@router.post("/sessions/{session_id}/resolve-help")
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


@router.post("/sessions/{session_id}/end")
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


@router.put("/menu/{item_id}/availability")
def set_availability(
    item_id: str, body: AvailabilityIn, kiosk: Kiosk = Depends(current_kiosk), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Staff marks a menu item sold out (available=false) or back in stock."""
    return service.set_item_availability(db, kiosk, item_id, body.available)
