"""The ordering logic: pairing, cart, orders, help and order status.

Every function takes the database session, the caller (a Device or a
Kiosk) and `now` (ms), changes the database inside one transaction, and
returns an *event* dict. The routers send that event to the kiosk and
the phone over WebSockets.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any, Optional, TypeVar

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError

from app import config
from app.errors import AppError
from app.logic import (
    STATUS_TIME_FIELD,
    build_order_lines,
    check_kiosk_id,
    check_token,
    check_transition,
    generate_token,
    kst_day,
    summarize_order,
    token_matches,
)
from app.models import Device, Kiosk, KioskSession, Order, Store

T = TypeVar("T")


def transact(db: Session, fn: Callable[[], T], attempts: int = 5) -> T:
    """Run fn and commit. If another request changed the same rows at the
    same moment (stale version or duplicate order number), roll back and
    run fn again with fresh data."""
    for attempt in range(attempts):
        try:
            result = fn()
            db.commit()
            return result
        except (StaleDataError, IntegrityError):
            db.rollback()
            if attempt == attempts - 1:
                raise
        except Exception:
            db.rollback()
            raise
    raise RuntimeError("unreachable")


def event(type_: str, kiosk_id: str, now: int, **fields: Any) -> dict[str, Any]:
    return {"type": type_, "kioskId": kiosk_id, "atMs": now, **fields}


def _is_idle(session: KioskSession, now: int) -> bool:
    return session.last_active_at + config.SESSION_IDLE_MS <= now


def _own_active_session(db: Session, device: Device, session_id: str, now: int) -> KioskSession:
    session = db.get(KioskSession, session_id)
    if session is None:
        raise AppError("session-not-found", "Connection not found. Please reconnect to the kiosk.")
    if session.device_id != device.id:
        raise AppError("not-your-session", "This connection belongs to someone else.")
    if session.status != "active" or _is_idle(session, now):
        raise AppError("session-expired", "The connection ended. Please reconnect to the kiosk.")
    return session


def _menu(db: Session, store_id: str) -> list[dict[str, Any]]:
    store = db.get(Store, store_id)
    if store is None:
        raise AppError("store-not-found", "Store not found.")
    return store.menu or []


def _cart_for(db: Session, store_id: str, items: Any) -> dict[str, Any]:
    if isinstance(items, list) and not items:
        return {"lines": [], "total": 0, "summary": ""}
    lines, total = build_order_lines(_menu(db, store_id), items)
    return {"lines": lines, "total": total, "summary": summarize_order(lines)}


# ---------- kiosk: rotating Bluetooth pairing token ----------


def kiosk_heartbeat(db: Session, kiosk: Kiosk, now: int) -> dict[str, Any]:
    """The kiosk calls this about every 30 s and broadcasts the returned
    token over Bluetooth. A phone must send back a current token to
    connect, which shows it is physically next to the kiosk."""

    def run() -> dict[str, Any]:
        db.refresh(kiosk)
        issued_at = (kiosk.current_expires_at or 0) - config.TOKEN_TTL_MS
        fresh = (
            kiosk.current_token
            and kiosk.current_expires_at is not None
            and now - issued_at < config.TOKEN_REFRESH_MS
            and kiosk.current_expires_at > now
        )
        if not fresh:
            kiosk.previous_token = kiosk.current_token
            kiosk.previous_expires_at = kiosk.current_expires_at
            kiosk.current_token = generate_token()
            kiosk.current_expires_at = now + config.TOKEN_TTL_MS
        kiosk.last_seen_at = now
        expires_at = kiosk.current_expires_at
        return {
            "kioskId": kiosk.id,
            "token": kiosk.current_token,
            "expiresAtMs": expires_at,
            "refreshInMs": max(1000, min(config.TOKEN_REFRESH_MS, expires_at - now - 5000)),
        }

    return transact(db, run)


# ---------- phone: connect to a kiosk ----------


def connect_to_kiosk(db: Session, device: Device, kiosk_id: Any, token: Any, now: int) -> dict[str, Any]:
    """The phone heard the kiosk's Bluetooth broadcast and sends back the kiosk
    ID and token. One phone at a time per kiosk; an idle phone is replaced."""
    kiosk_id = check_kiosk_id(kiosk_id)
    token = check_token(token)

    def run() -> dict[str, Any]:
        kiosk = db.get(Kiosk, kiosk_id, populate_existing=True)
        if kiosk is None:
            raise AppError("kiosk-not-found", "Kiosk not found.")
        if not token_matches(
            token, kiosk.current_token, kiosk.current_expires_at, kiosk.previous_token, kiosk.previous_expires_at, now
        ):
            raise AppError("token-invalid", "Could not verify the kiosk. Move closer and try again.")
        store = db.get(Store, kiosk.store_id)

        def connected(session_id: str) -> dict[str, Any]:
            return event(
                "connected",
                kiosk.id,
                now,
                sessionId=session_id,
                storeId=kiosk.store_id,
                kioskName=kiosk.name or kiosk.id,
                storeName=store.name if store else None,
            )

        previous = db.get(KioskSession, kiosk.active_session_id, populate_existing=True) if kiosk.active_session_id else None
        if previous is not None and previous.status == "active" and not _is_idle(previous, now):
            if previous.device_id == device.id:
                previous.last_active_at = now  # same phone reconnecting
                return connected(previous.id)
            raise AppError("kiosk-busy", "Someone else is using this kiosk from their phone. Please wait a moment.")
        if previous is not None and previous.status == "active":
            previous.status = "expired"
            previous.ended_at = now

        session = KioskSession(
            id=str(uuid.uuid4()),
            kiosk_id=kiosk.id,
            store_id=kiosk.store_id,
            device_id=device.id,
            status="active",
            created_at=now,
            last_active_at=now,
            help_requested=False,
            cart={"lines": [], "total": 0, "summary": ""},
        )
        db.add(session)
        kiosk.active_session_id = session.id
        return connected(session.id)

    return transact(db, run)


# ---------- phone: live cart shown on the kiosk ----------


def sync_cart(db: Session, device: Device, session_id: str, items: Any, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        session = _own_active_session(db, device, session_id, now)
        cart = _cart_for(db, session.store_id, items)
        session.cart = cart
        session.last_active_at = now
        return event(
            "cart", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id,
            total=cart["total"], summary=cart["summary"], lines=cart["lines"],
        )

    return transact(db, run)


# ---------- phone: place the order ----------


def submit_order(
    db: Session, device: Device, session_id: str, items: Any, payment_method: str, note: str, now: int
) -> dict[str, Any]:
    if payment_method not in config.PAYMENT_METHODS:
        raise AppError("bad-payment-method", f"paymentMethod must be one of: {', '.join(config.PAYMENT_METHODS)}.")
    if not isinstance(note, str) or len(note) > config.MAX_NOTE_LENGTH:
        raise AppError("bad-note", f"Note must be text up to {config.MAX_NOTE_LENGTH} characters.")

    def run() -> dict[str, Any]:
        session = _own_active_session(db, device, session_id, now)
        lines, total = build_order_lines(_menu(db, session.store_id), items)
        summary = summarize_order(lines)
        day = kst_day(now)
        last = db.scalar(
            select(func.max(Order.order_number)).where(Order.store_id == session.store_id, Order.kst_day == day)
        )
        order = Order(
            id=str(uuid.uuid4()),
            store_id=session.store_id,
            kiosk_id=session.kiosk_id,
            session_id=session.id,
            device_id=device.id,
            kst_day=day,
            order_number=(last or 0) + 1,
            lines=lines,
            total=total,
            summary=summary,
            note=note.strip(),
            payment_method=payment_method,
            status="submitted",
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        session.status = "ordered"
        session.order_id = order.id
        session.last_active_at = now
        session.ended_at = now
        kiosk = db.get(Kiosk, session.kiosk_id, populate_existing=True)
        if kiosk is not None and kiosk.active_session_id == session.id:
            kiosk.active_session_id = None
        db.flush()  # a duplicate order number fails here and is retried
        return event(
            "ordered", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id, orderId=order.id,
            orderNumber=order.order_number, total=total, summary=summary, status="submitted",
            paymentMethod=payment_method, note=order.note,
        )

    return transact(db, run)


# ---------- help ----------


def request_help(db: Session, device: Device, session_id: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        session = _own_active_session(db, device, session_id, now)
        session.help_requested = True
        session.help_requested_at = now
        session.last_active_at = now
        return event("help", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id)

    return transact(db, run)


def resolve_help(db: Session, kiosk: Kiosk, session_id: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        session = db.get(KioskSession, session_id, populate_existing=True)
        if session is None or session.kiosk_id != kiosk.id:
            raise AppError("session-not-found", "Session not found for this kiosk.")
        session.help_requested = False
        session.help_resolved_at = now
        return event("help_resolved", kiosk.id, now, sessionId=session.id, storeId=session.store_id)

    return transact(db, run)


# ---------- disconnect (phone or kiosk) ----------


def end_session(db: Session, caller: Device | Kiosk, session_id: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        session = db.get(KioskSession, session_id, populate_existing=True)
        if session is None:
            raise AppError("session-not-found", "Session not found.")
        allowed = session.kiosk_id == caller.id if isinstance(caller, Kiosk) else session.device_id == caller.id
        if not allowed:
            raise AppError("not-your-session", "You cannot end this session.")
        if session.status == "active":
            session.status = "ended"
            session.ended_at = now
        kiosk = db.get(Kiosk, session.kiosk_id, populate_existing=True)
        if kiosk is not None and kiosk.active_session_id == session.id:
            kiosk.active_session_id = None
        return event("ended", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id, status=session.status)

    return transact(db, run)


# ---------- orders ----------


def update_order_status(db: Session, kiosk: Kiosk, order_id: str, status: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        order = db.get(Order, order_id, populate_existing=True)
        if order is None or order.store_id != kiosk.store_id:
            raise AppError("order-not-found", "Order not found in this store.")
        check_transition(order.status, status)
        order.status = status
        order.updated_at = now
        setattr(order, STATUS_TIME_FIELD[status], now)
        if status == "cancelled":
            order.cancelled_by = "staff"
        return event(
            "order_status", order.kiosk_id, now, sessionId=order.session_id, storeId=order.store_id,
            orderId=order.id, orderNumber=order.order_number, status=status,
        )

    return transact(db, run)


def cancel_my_order(db: Session, device: Device, order_id: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        order = db.get(Order, order_id, populate_existing=True)
        if order is None or order.device_id != device.id:
            raise AppError("order-not-found", "Order not found.")
        if order.status != "submitted":
            raise AppError("too-late-to-cancel", "Staff already started this order. Please ask at the counter.")
        order.status = "cancelled"
        order.updated_at = now
        order.cancelled_at = now
        order.cancelled_by = "customer"
        return event(
            "order_status", order.kiosk_id, now, sessionId=order.session_id, storeId=order.store_id,
            orderId=order.id, orderNumber=order.order_number, status="cancelled",
        )

    return transact(db, run)


def order_dict(order: Order) -> dict[str, Any]:
    return {
        "orderId": order.id,
        "orderNumber": order.order_number,
        "kioskId": order.kiosk_id,
        "sessionId": order.session_id,
        "status": order.status,
        "total": order.total,
        "summary": order.summary,
        "lines": order.lines,
        "note": order.note,
        "paymentMethod": order.payment_method,
        "createdAtMs": order.created_at,
        "updatedAtMs": order.updated_at,
    }


def get_my_order(db: Session, device: Device, order_id: str) -> dict[str, Any]:
    order = db.get(Order, order_id)
    if order is None or order.device_id != device.id:
        raise AppError("order-not-found", "Order not found.")
    return order_dict(order)


def session_dict(session: KioskSession) -> dict[str, Any]:
    return {
        "sessionId": session.id,
        "kioskId": session.kiosk_id,
        "storeId": session.store_id,
        "status": session.status,
        "helpRequested": session.help_requested,
        "cart": session.cart,
        "orderId": session.order_id,
        "lastActiveAtMs": session.last_active_at,
    }


def get_my_session(db: Session, device: Device, session_id: str) -> dict[str, Any]:
    session = db.get(KioskSession, session_id)
    if session is None or session.device_id != device.id:
        raise AppError("session-not-found", "Session not found.")
    return session_dict(session)


def kiosk_active_session(db: Session, kiosk: Kiosk, now: int) -> Optional[dict[str, Any]]:
    """What the kiosk screen should show after a restart."""
    db.refresh(kiosk)
    if not kiosk.active_session_id:
        return None
    session = db.get(KioskSession, kiosk.active_session_id)
    if session is None or session.status != "active" or _is_idle(session, now):
        return None
    return session_dict(session)


def kiosk_orders(db: Session, kiosk: Kiosk, now: int, status: Optional[str] = None) -> list[dict[str, Any]]:
    """Today's orders for the kiosk's store, newest first."""
    query = select(Order).where(Order.store_id == kiosk.store_id, Order.kst_day == kst_day(now))
    if status:
        query = query.where(Order.status == status)
    return [order_dict(o) for o in db.scalars(query.order_by(Order.created_at.desc()))]


# ---------- staff: sold out ----------


def set_item_availability(db: Session, kiosk: Kiosk, item_id: str, available: bool) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        store = db.get(Store, kiosk.store_id, populate_existing=True)
        if store is None:
            raise AppError("store-not-found", "Store not found.")
        menu = [dict(m) for m in store.menu or []]
        item = next((m for m in menu if m.get("id") == item_id), None)
        if item is None:
            raise AppError("unknown-item", "Item not on this menu.")
        item["available"] = available
        store.menu = menu  # assign a new list so SQLAlchemy saves the change
        return {"itemId": item_id, "available": available}

    return transact(db, run)
