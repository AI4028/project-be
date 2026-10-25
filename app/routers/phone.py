"""Endpoints the phone app calls. Send `Authorization: Bearer dev_...`."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.orm import Session

from app import service
from app.auth import create_device, current_device
from app.clock import get_now
from app.db import get_db
from app.models import Device
from app.realtime import hub
from app.schemas import CartIn, ConnectIn, OrderIn

router = APIRouter(tags=["phone"])


@router.post("/devices", status_code=201)
def register_device(db: Session = Depends(get_db), now: int = Depends(get_now)) -> dict[str, Any]:
    """First launch: get an anonymous token. Store it on the phone (Keychain)."""
    device, token = create_device(db, now)
    return {"deviceId": device.id, "token": token}


@router.post("/sessions", status_code=201)
def connect(
    body: ConnectIn,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    """Connect to the kiosk whose Bluetooth broadcast the phone heard."""
    ev = service.connect_to_kiosk(db, device, body.kiosk_id, body.token, now)
    background.add_task(hub.publish, ev)
    return ev


@router.get("/sessions/{session_id}")
def get_session(session_id: str, device: Device = Depends(current_device), db: Session = Depends(get_db)) -> dict[str, Any]:
    return service.get_my_session(db, device, session_id)


@router.put("/sessions/{session_id}/cart")
def update_cart(
    session_id: str,
    body: CartIn,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    """Replace the cart; the kiosk screen shows it live. Send [] to clear."""
    ev = service.sync_cart(db, device, session_id, body.items, now)
    background.add_task(hub.publish, ev)
    return ev


@router.post("/sessions/{session_id}/order", status_code=201)
def place_order(
    session_id: str,
    body: OrderIn,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    ev = service.submit_order(db, device, session_id, body.items, body.payment_method, body.note, now)
    background.add_task(hub.publish, ev)
    return ev


@router.post("/sessions/{session_id}/help")
def ask_for_help(
    session_id: str,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    ev = service.request_help(db, device, session_id, now)
    background.add_task(hub.publish, ev)
    return ev


@router.post("/sessions/{session_id}/end")
def disconnect(
    session_id: str,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    ev = service.end_session(db, device, session_id, now)
    background.add_task(hub.publish, ev)
    return ev


@router.get("/orders/{order_id}")
def get_order(order_id: str, device: Device = Depends(current_device), db: Session = Depends(get_db)) -> dict[str, Any]:
    return service.get_my_order(db, device, order_id)


@router.post("/orders/{order_id}/cancel")
def cancel_order(
    order_id: str,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    ev = service.cancel_my_order(db, device, order_id, now)
    background.add_task(hub.publish, ev)
    return ev
