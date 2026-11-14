"""Phone endpoints. Auth: `Bearer dev_...`."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Header
from sqlalchemy.orm import Session

from app.responses import CartEvent, Connected, DeviceOut, Ended, HelpEvent, OrderEvent, OrderOut, Ordered, SessionOut
from app import service
from app.auth import create_device, current_device
from app.clock import get_now
from app.db import get_db
from app.models import Device
from app.limits import registration_limit, pairing_limit
from app.realtime import hub
from app.schemas import CartIn, ConnectIn, OrderIn
from app.responses import PhoneState
from app.routers.public import get_store

router = APIRouter(tags=["phone"])


@router.get("/sessions/{session_id}/state", response_model=PhoneState, response_model_exclude_unset=True)
def phone_state(session_id: str, device: Device = Depends(current_device),
                db: Session = Depends(get_db), now: int = Depends(get_now)):
    """Restore session, order and menu after a connection gap."""
    session = service.get_my_session(db, device, session_id, now)
    order = service.get_my_order(db, device, session["orderId"]) if session["orderId"] else None
    return {"session": session, "order": order, "store": get_store(session["storeId"], db)}


@router.delete("/devices/me")
def revoke_device(background: BackgroundTasks, device: Device = Depends(current_device),
                  db: Session = Depends(get_db), now: int = Depends(get_now)):
    """Revoke this token, release active kiosks, and close this phone's sockets."""
    events, ids = service.revoke_device(db, device, now)
    for event in events:
        background.add_task(hub.publish, event)
    for sid in ids:
        background.add_task(hub.close, f"session:{sid}")
    return {"status": "revoked"}


@router.post("/devices", dependencies=[Depends(registration_limit)], status_code=201, response_model=DeviceOut, response_model_exclude_unset=True)
def register_device(db: Session = Depends(get_db), now: int = Depends(get_now)) -> dict[str, Any]:
    """First launch: get an anonymous token to keep on the device."""
    device, token = create_device(db, now)
    return {"deviceId": device.id, "token": token}


@router.post("/sessions", dependencies=[Depends(pairing_limit)], status_code=201, response_model=Connected, response_model_exclude_unset=True)
def connect(
    body: ConnectIn,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    """Pair with the kiosk whose Bluetooth token the phone heard."""
    ev = service.connect_to_kiosk(db, device, body.kiosk_id, body.token, now)
    background.add_task(hub.publish, ev)
    return ev


@router.get("/sessions/{session_id}", response_model=SessionOut, response_model_exclude_unset=True)
def get_session(session_id: str, device: Device = Depends(current_device), db: Session = Depends(get_db), now: int = Depends(get_now)) -> dict[str, Any]:
    return service.get_my_session(db, device, session_id, now)


@router.put("/sessions/{session_id}/cart", response_model=CartEvent, response_model_exclude_unset=True)
def update_cart(
    session_id: str,
    body: CartIn,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
) -> dict[str, Any]:
    """Replace the cart (shown live on the kiosk). [] clears it."""
    ev = service.sync_cart(db, device, session_id, body.items, now)
    background.add_task(hub.publish, ev)
    return ev


@router.post("/sessions/{session_id}/order", status_code=201, response_model=Ordered, response_model_exclude_unset=True)
def place_order(
    session_id: str,
    body: OrderIn,
    background: BackgroundTasks,
    device: Device = Depends(current_device),
    db: Session = Depends(get_db),
    now: int = Depends(get_now),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
) -> dict[str, Any]:
    ev = service.submit_order(db, device, session_id, body.items, body.payment_method, body.note, now, body.quote_id, idempotency_key)
    background.add_task(hub.publish, ev)
    return ev


@router.post("/sessions/{session_id}/help", response_model=HelpEvent, response_model_exclude_unset=True)
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


@router.post("/sessions/{session_id}/end", response_model=Ended, response_model_exclude_unset=True)
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


@router.get("/orders/{order_id}", response_model=OrderOut, response_model_exclude_unset=True)
def get_order(order_id: str, device: Device = Depends(current_device), db: Session = Depends(get_db)) -> dict[str, Any]:
    return service.get_my_order(db, device, order_id)


@router.post("/orders/{order_id}/cancel", response_model=OrderEvent, response_model_exclude_unset=True)
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
