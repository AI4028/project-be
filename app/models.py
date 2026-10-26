"""Database tables. All times are milliseconds since 1970 (UTC), stored as integers."""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import JSON, BigInteger, Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Store(Base):
    """A store, its accessibility info and its menu (menu kept as JSON)."""

    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[Optional[str]] = mapped_column(String(200))
    address: Mapped[Optional[str]] = mapped_column(String(300))
    lat: Mapped[Optional[float]] = mapped_column(Float)
    lng: Mapped[Optional[float]] = mapped_column(Float)
    geofence_radius_m: Mapped[Optional[int]] = mapped_column(Integer)
    ordering_methods: Mapped[list[str]] = mapped_column(JSON, default=list)
    accessibility: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    kiosk_features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    indoor_directions: Mapped[Optional[str]] = mapped_column(Text)
    # [{id, name, nameEn, category, sortOrder, price, available, description,
    #   options: [{id, name, type, required, maxChoices,
    #              choices: [{id, name, priceDelta, available}]}]}]
    menu: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class Kiosk(Base):
    """A kiosk. Its id is a 4-character code (e.g. GK01) sent over Bluetooth."""

    __tablename__ = "kiosks"

    id: Mapped[str] = mapped_column(String(4), primary_key=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"))
    name: Mapped[Optional[str]] = mapped_column(String(100))
    name_en: Mapped[Optional[str]] = mapped_column(String(100))
    # SHA-256 of the kiosk's API key (the key itself is never stored).
    api_key_hash: Mapped[Optional[str]] = mapped_column(String(64), unique=True)
    # Rotating Bluetooth pairing token.
    current_token: Mapped[Optional[str]] = mapped_column(String(16))
    current_expires_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    previous_token: Mapped[Optional[str]] = mapped_column(String(16))
    previous_expires_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    active_session_id: Mapped[Optional[str]] = mapped_column(String(36))
    last_seen_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    # Optimistic locking: two requests changing the same kiosk at once
    # cannot both succeed; the loser is retried (see service.transact).
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class Device(Base):
    """A phone. Phones get an anonymous token from POST /devices; no sign-up."""

    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[int] = mapped_column(BigInteger)


class KioskSession(Base):
    """One phone connected to one kiosk."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    kiosk_id: Mapped[str] = mapped_column(ForeignKey("kiosks.id"))
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    status: Mapped[str] = mapped_column(String(16))  # active | ordered | ended | expired
    created_at: Mapped[int] = mapped_column(BigInteger)
    last_active_at: Mapped[int] = mapped_column(BigInteger)
    ended_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    help_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    help_requested_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    help_resolved_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    cart: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # {lines, total, summary}
    order_id: Mapped[Optional[str]] = mapped_column(String(36))
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        # Two orders can never get the same number on the same day.
        UniqueConstraint("store_id", "kst_day", "order_number", name="uq_order_number_per_day"),
        Index("ix_orders_store_created", "store_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"))
    kiosk_id: Mapped[str] = mapped_column(ForeignKey("kiosks.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    device_id: Mapped[str] = mapped_column(ForeignKey("devices.id"))
    kst_day: Mapped[str] = mapped_column(String(10))  # "2026-10-08"
    order_number: Mapped[int] = mapped_column(Integer)
    lines: Mapped[list[dict[str, Any]]] = mapped_column(JSON)
    total: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    note: Mapped[str] = mapped_column(Text, default="")
    payment_method: Mapped[str] = mapped_column(String(16))
    # submitted | accepted | preparing | ready | picked_up | cancelled
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)
    accepted_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    preparing_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    ready_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    picked_up_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    cancelled_at: Mapped[Optional[int]] = mapped_column(BigInteger)
    cancelled_by: Mapped[Optional[str]] = mapped_column(String(16))
