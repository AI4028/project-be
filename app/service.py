"""Ordering flow: pairing, cart, orders, help, status.

Each mutation runs in one transaction and returns an event dict that the
routers publish to the kiosk and phone.
"""

from __future__ import annotations

import uuid
import hashlib
import json
from collections.abc import Callable
from typing import Any, TypeVar

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
    """Run fn and commit, retrying on a concurrent write (stale version or duplicate order number)."""
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


def event(type_: str, kiosk_id: str | None, now: int, **fields: Any) -> dict[str, Any]:
    return {"type": type_, "kioskId": kiosk_id, "atMs": now, **fields}


def _is_idle(session: KioskSession, now: int) -> bool:
    return session.last_active_at + config.SESSION_IDLE_MS <= now


def _release_kiosk(db: Session, session: KioskSession) -> None:
    if session.kiosk_id is not None:
        kiosk = db.get(Kiosk, session.kiosk_id, populate_existing=True)
        if kiosk is not None and kiosk.active_session_id == session.id:
            kiosk.active_session_id = None


def _own_active_session(db: Session, device: Device, session_id: str, now: int) -> KioskSession:
    session = db.get(KioskSession, session_id)
    if session is None:
        raise AppError("session-not-found", "Connection not found. Please reconnect to the kiosk.")
    if session.device_id != device.id:
        raise AppError("not-your-session", "This connection belongs to someone else.")
    if session.status != "active" or _is_idle(session, now):
        raise AppError("session-expired", "The connection ended. Please reconnect to the kiosk.")
    return session


def store_menu(db: Session, store_id: str, lock: bool = False) -> list[dict[str, Any]]:
    store = (db.scalar(select(Store).where(Store.id == store_id).with_for_update()
                       .execution_options(populate_existing=True)) if lock else db.get(Store, store_id))
    if store is None:
        raise AppError("store-not-found", "Store not found.")
    return store.menu or []


def _cart_for(db: Session, store_id: str, items: Any) -> dict[str, Any]:
    if isinstance(items, list) and not items:
        return {"lines": [], "total": 0, "summary": ""}
    lines, total = build_order_lines(store_menu(db, store_id), items)
    return {"lines": lines, "total": total, "summary": summarize_order(lines)}


# ---------- kiosk: rotating Bluetooth pairing token ----------


def kiosk_heartbeat(db: Session, kiosk: Kiosk, now: int, mark_seen: bool = True) -> dict[str, Any]:
    """Rotate the Bluetooth pairing token. Echoing a current token proves a phone is at the kiosk.

    mark_seen=False rotates without recording a check-in (demo token shortcut).
    """

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
        if mark_seen:
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
    """Pair a phone with a kiosk. One phone per kiosk; an idle one is replaced."""
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
        in_use = previous is not None and previous.status == "active" and not _is_idle(previous, now)
        if in_use and previous.device_id == device.id:
            previous.last_active_at = now  # same phone reconnecting
            return connected(previous.id)
        if store is not None and store.ordering_paused:
            raise AppError("ordering-paused", "This store is not taking phone orders right now.")
        if in_use:
            raise AppError("kiosk-busy", "Someone else is using this kiosk from their phone. Please wait a moment.")
        # Cleanup expires the old session and emits its event. It checks the
        # active-session pointer, so it cannot release this new connection.

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


def start_store_session(db: Session, device: Device, store_id: str, now: int, *, items: list | None = None) -> dict[str, Any]:
    """Give the phone its own cart without entering the kiosk's active-session slot."""
    def run() -> dict[str, Any]:
        store = db.get(Store, store_id, populate_existing=True, with_for_update=True)
        if store is None:
            raise AppError("store-not-found", "Store not found.")
        if store.ordering_paused:
            raise AppError("ordering-paused", "This store is not taking phone orders right now.")
        staff_terminal = db.scalar(select(Kiosk.id).where(
            Kiosk.store_id == store_id, Kiosk.api_key_hash.is_not(None),
        ).limit(1))
        if staff_terminal is None:
            raise AppError("ordering-unavailable", "This store is not set up to receive phone orders.")
        # Validate and price a replacement before accepting the destination cart.
        cart = None
        if items is not None:
            if not items:
                raise AppError("bad-request", "Choose an item before switching stores.")
            cart = _cart_for(db, store_id, items)
            cart["quoteId"] = str(uuid.uuid4())
        existing = db.scalar(select(KioskSession).where(
            KioskSession.device_id == device.id,
            KioskSession.store_id == store_id,
            KioskSession.kiosk_id.is_(None),
            KioskSession.status == "active",
        ).with_for_update().execution_options(populate_existing=True))
        if existing is not None:
            if not _is_idle(existing, now):
                if cart is not None:
                    existing.cart = cart
                existing.last_active_at = now
                return session_dict(existing)
            existing.status = "expired"
            existing.ended_at = now
            db.flush()
        session = KioskSession(
            id=str(uuid.uuid4()),
            store_id=store_id,
            device_id=device.id,
            status="active",
            created_at=now,
            last_active_at=now,
            help_requested=False,
            cart=cart or {"lines": [], "total": 0, "summary": ""},
        )
        db.add(session)
        return session_dict(session)

    return transact(db, run)


# ---------- phone: server-priced cart ----------


def sync_cart(db: Session, device: Device, session_id: str, items: Any, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        session = _own_active_session(db, device, session_id, now)
        cart = _cart_for(db, session.store_id, items)
        cart["quoteId"] = str(uuid.uuid4())
        session.cart = cart
        session.last_active_at = now
        return event(
            "cart", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id,
            total=cart["total"], summary=cart["summary"], lines=cart["lines"], quoteId=cart["quoteId"],
        )

    return transact(db, run)


# ---------- phone: place the order ----------


def submit_order(
    db: Session, device: Device, session_id: str, items: Any, payment_method: str, note: str, now: int,
    quote_id: str | None = None, request_key: str | None = None, *, simulate_payment: bool = False,
) -> dict[str, Any]:
    if payment_method not in config.PAYMENT_METHODS:
        raise AppError("bad-payment-method", f"paymentMethod must be one of: {', '.join(config.PAYMENT_METHODS)}.")
    if not isinstance(note, str) or len(note) > config.MAX_NOTE_LENGTH:
        raise AppError("bad-note", f"Note must be text up to {config.MAX_NOTE_LENGTH} characters.")

    if request_key is not None and not 8 <= len(request_key) <= 128:
        raise AppError("bad-request-key", "Idempotency-Key must be 8-128 characters.")
    details = {"items": items, "paymentMethod": payment_method, "note": note, "quoteId": quote_id}
    if simulate_payment:
        details["simulatePayment"] = True
    fingerprint = hashlib.sha256(json.dumps(
        details,
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode()).hexdigest()

    def run() -> dict[str, Any]:
        session = db.scalar(select(KioskSession).where(KioskSession.id == session_id)
                            .with_for_update().execution_options(populate_existing=True))
        if session is not None and session.device_id == device.id and request_key and session.submission:
            saved = session.submission
            if saved["key"] == request_key:
                if saved["hash"] != fingerprint:
                    raise AppError("idempotency-conflict", "This request key was used with different order details.")
                return saved["event"]
        if simulate_payment and not config.DEMO_MODE:
            raise AppError("bad-payment-method", "Simulated payments are available only in demo mode.")
        if not simulate_payment and payment_method not in ("counter", "kiosk"):
            raise AppError("bad-payment-method", "Choose payment at the cafe.")
        session = _own_active_session(db, device, session_id, now)
        lines, total = build_order_lines(store_menu(db, session.store_id, lock=True), items)
        if db.get(Store, session.store_id).ordering_paused:
            raise AppError("ordering-paused", "This store is not taking phone orders right now.")
        if session.kiosk_id is None and (not quote_id or not request_key):
            raise AppError("price-changed", "Review a current quote before sending an order.")
        if quote_id is not None and (session.cart.get("quoteId") != quote_id
                                    or session.cart.get("lines") != lines or session.cart.get("total") != total):
            raise AppError("price-changed", "Refresh the cart and confirm its current price before ordering.")
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
            simulated_approved_amount=total if simulate_payment else None,
            status="submitted",
            created_at=now,
            updated_at=now,
        )
        db.add(order)
        session.status = "ordered"
        session.order_id = order.id
        session.last_active_at = now
        session.ended_at = now
        _release_kiosk(db, session)
        db.flush()  # a duplicate order number fails here and is retried
        result = event(
            "ordered", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id, orderId=order.id,
            orderNumber=order.order_number, total=total, summary=summary, lines=lines, status="submitted",
            simulatedApprovedAmount=order.simulated_approved_amount,
            paymentMethod=payment_method, note=order.note, createdAtMs=order.created_at, updatedAtMs=order.updated_at,
        )
        if request_key:
            session.submission = {"key": request_key, "hash": fingerprint, "event": result}
        return result

    return transact(db, run)


# ---------- help ----------


def request_help(db: Session, device: Device, session_id: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        session = _own_active_session(db, device, session_id, now)
        session.help_requested = True
        session.help_requested_at = now
        session.help_resolved_at = None
        session.last_active_at = now
        return event("help", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id)

    return transact(db, run)


def request_order_help(db: Session, device: Device, order_id: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        order = db.get(Order, order_id, populate_existing=True)
        if order is None or order.device_id != device.id:
            raise AppError("order-not-found", "Order not found.")
        if order.status in {"picked_up", "cancelled"}:
            raise AppError("bad-transition", "This order has already ended.")
        session = db.get(KioskSession, order.session_id, populate_existing=True)
        if session is None:
            raise AppError("session-not-found", "Session not found.")
        if not session.help_requested:
            session.help_requested = True
            session.help_requested_at = now
            session.help_resolved_at = None
        return event(
            "help", session.kiosk_id, now, sessionId=session.id, storeId=order.store_id,
            orderId=order.id, orderNumber=order.order_number,
        )
    return transact(db, run)


def resolve_help(db: Session, kiosk: Kiosk, session_id: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        session = db.get(KioskSession, session_id, populate_existing=True)
        if session is None or session.store_id != kiosk.store_id or (
            session.kiosk_id is not None and session.kiosk_id != kiosk.id and session.status != "ordered"
        ):
            raise AppError("session-not-found", "Session not found for this kiosk.")
        session.help_requested = False
        session.help_resolved_at = now
        return event("help_resolved", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id,
                     orderId=session.order_id)

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
        _release_kiosk(db, session)
        return event("ended", session.kiosk_id, now, sessionId=session.id, storeId=session.store_id, status=session.status)

    return transact(db, run)


# ---------- orders ----------


def update_order_status(db: Session, kiosk: Kiosk, order_id: str, status: str, now: int) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        order = db.scalar(select(Order).where(Order.id == order_id)
                          .with_for_update().execution_options(populate_existing=True))
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
        order = db.scalar(select(Order).where(Order.id == order_id)
                          .with_for_update().execution_options(populate_existing=True))
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
        "storeId": order.store_id,
        "sessionId": order.session_id,
        "status": order.status,
        "total": order.total,
        "summary": order.summary,
        "lines": order.lines,
        "note": order.note,
        "paymentMethod": order.payment_method,
        "simulatedApprovedAmount": order.simulated_approved_amount,
        "createdAtMs": order.created_at,
        "updatedAtMs": order.updated_at,
        "cancelledBy": order.cancelled_by,
    }


def _help_state(session: KioskSession | None) -> str:
    if session is None:
        return "idle"
    if session.help_requested:
        return "sent"
    if session.help_resolved_at is not None:
        return "acknowledged"
    return "idle"


def get_my_order(db: Session, device: Device, order_id: str) -> dict[str, Any]:
    order = db.get(Order, order_id)
    if order is None or order.device_id != device.id:
        raise AppError("order-not-found", "Order not found.")
    session = db.get(KioskSession, order.session_id)
    return {
        **order_dict(order),
        "helpState": _help_state(session),
    }


def get_my_orders(db: Session, device: Device) -> list[dict[str, Any]]:
    query = select(Order).where(Order.device_id == device.id).order_by(
        Order.created_at.desc(), Order.order_number.desc(), Order.id,
    ).limit(50)
    return [order_dict(order) for order in db.scalars(query)]


def session_dict(session: KioskSession) -> dict[str, Any]:
    return {
        "sessionId": session.id,
        "kioskId": session.kiosk_id,
        "storeId": session.store_id,
        "status": session.status,
        "helpRequested": session.help_requested,
        "helpState": _help_state(session),
        "cart": session.cart,
        "orderId": session.order_id,
        "lastActiveAtMs": session.last_active_at,
    }


def get_my_session(db: Session, device: Device, session_id: str, now: int | None = None) -> dict[str, Any]:
    session = db.get(KioskSession, session_id)
    if session is None or session.device_id != device.id:
        raise AppError("session-not-found", "Session not found.")
    result = session_dict(session)
    if now is not None and session.status == "active" and _is_idle(session, now):
        result["status"] = "expired"
    return result


def expire_sessions(db: Session, now: int) -> list[dict[str, Any]]:
    """Persist idle expiry and release kiosks; publish returned events after commit."""
    def run():
        events = []
        sessions = db.scalars(select(KioskSession).where(
            KioskSession.status == "active",
            KioskSession.last_active_at <= now - config.SESSION_IDLE_MS,
        ).with_for_update().execution_options(populate_existing=True))
        for session in sessions:
            session.status = "expired"
            session.ended_at = now
            _release_kiosk(db, session)
            events.append(event("ended", session.kiosk_id, now, sessionId=session.id,
                                storeId=session.store_id, status="expired"))
        return events
    return transact(db, run)


def kiosk_active_session(db: Session, kiosk: Kiosk, now: int) -> dict[str, Any] | None:
    """The live session, so a restarted kiosk can restore its screen."""
    db.refresh(kiosk)
    if not kiosk.active_session_id:
        return None
    session = db.get(KioskSession, kiosk.active_session_id)
    if session is None or session.status != "active" or _is_idle(session, now):
        return None
    return session_dict(session)


def kiosk_orders(db: Session, kiosk: Kiosk, now: int, status: str | None = None) -> list[dict[str, Any]]:
    """Today's orders for the kiosk's store, newest first."""
    query = select(Order).where(Order.store_id == kiosk.store_id, Order.kst_day == kst_day(now))
    if status:
        query = query.where(Order.status == status)
    return [order_dict(o) for o in db.scalars(query.order_by(Order.created_at.desc()))]


def kiosk_help_requests(db: Session, kiosk: Kiosk, now: int) -> list[dict[str, Any]]:
    query = select(KioskSession, Order.order_number).outerjoin(Order, Order.id == KioskSession.order_id).where(
        KioskSession.store_id == kiosk.store_id,
        KioskSession.help_requested.is_(True),
        (
            (KioskSession.kiosk_id.is_(None) & (KioskSession.status == "active") &
             (KioskSession.last_active_at > now - config.SESSION_IDLE_MS))
            | ((KioskSession.status == "ordered") & Order.status.in_(("submitted", "accepted", "preparing", "ready")))
        ),
    ).order_by(KioskSession.help_requested_at, KioskSession.id)
    return [
        {"sessionId": session.id, "orderNumber": number}
        for session, number in db.execute(query)
    ]


# ---------- staff: sold out ----------


def set_ordering_paused(db: Session, kiosk: Kiosk, paused: bool) -> dict[str, Any]:
    """Staff pause or resume phone ordering for the kiosk's store."""
    def run() -> dict[str, Any]:
        store = db.scalar(select(Store).where(Store.id == kiosk.store_id)
                          .with_for_update().execution_options(populate_existing=True))
        if store is None:
            raise AppError("store-not-found", "Store not found.")
        store.ordering_paused = paused
        return {"storeId": store.id, "orderingPaused": paused}

    return transact(db, run)


def update_menu_item(db: Session, store_id: str, item_id: str, changes: dict[str, Any]) -> dict[str, Any]:
    def run() -> dict[str, Any]:
        store = db.scalar(select(Store).where(Store.id == store_id)
                          .with_for_update().execution_options(populate_existing=True))
        if store is None:
            raise AppError("store-not-found", "Store not found.")
        menu = [dict(m) for m in store.menu or []]
        item = next((m for m in menu if m.get("id") == item_id), None)
        if item is None:
            raise AppError("unknown-item", "Item not on this menu.")
        item.update(changes)
        store.menu = menu  # new list so SQLAlchemy detects the change
        return {"itemId": item_id, **changes}

    return transact(db, run)


def revoke_device(db: Session, device: Device, now: int):
    """Invalidate a phone token and release its sessions in one transaction."""
    from app.auth import hash_token, new_device_token

    def run():
        db.refresh(device)
        device.token_hash = hash_token(new_device_token())
        events, ids = [], []
        for session in db.scalars(select(KioskSession).where(KioskSession.device_id == device.id)
                                  .with_for_update().execution_options(populate_existing=True)):
            ids.append(session.id)
            if session.status == "active":
                session.status = "ended"
                session.ended_at = now
                _release_kiosk(db, session)
                events.append(event("ended", session.kiosk_id, now, sessionId=session.id,
                                            storeId=session.store_id, status="ended"))
        return events, ids
    return transact(db, run)
