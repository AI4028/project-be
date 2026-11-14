"""Database tables. Times are Unix epoch milliseconds."""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Store(Base):
    """A store with its accessibility info and JSON menu."""

    __tablename__ = "stores"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    name_en: Mapped[str | None] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(300))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    geofence_radius_m: Mapped[int | None] = mapped_column(Integer)
    ordering_methods: Mapped[list[str]] = mapped_column(JSON, default=list)
    accessibility: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    kiosk_features: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    indoor_directions: Mapped[str | None] = mapped_column(Text)
    # [{id, name, nameEn, category, sortOrder, price, available, description,
    #   options: [{id, name, type, required, maxChoices,
    #              choices: [{id, name, priceDelta, available}]}]}]
    menu: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)


class Kiosk(Base):
    """A kiosk. The id is the 4-character code it broadcasts (e.g. GK01)."""

    __tablename__ = "kiosks"

    id: Mapped[str] = mapped_column(String(4), primary_key=True)
    store_id: Mapped[str] = mapped_column(ForeignKey("stores.id"))
    name: Mapped[str | None] = mapped_column(String(100))
    name_en: Mapped[str | None] = mapped_column(String(100))
    api_key_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    # Rotating Bluetooth pairing token.
    current_token: Mapped[str | None] = mapped_column(String(16))
    current_expires_at: Mapped[int | None] = mapped_column(BigInteger)
    previous_token: Mapped[str | None] = mapped_column(String(16))
    previous_expires_at: Mapped[int | None] = mapped_column(BigInteger)
    active_session_id: Mapped[str | None] = mapped_column(String(36))
    last_seen_at: Mapped[int | None] = mapped_column(BigInteger)
    # Optimistic lock: concurrent writers can't both win; the loser retries (service.transact).
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class Device(Base):
    """An anonymous phone (POST /devices, no sign-up)."""

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
    ended_at: Mapped[int | None] = mapped_column(BigInteger)
    help_requested: Mapped[bool] = mapped_column(Boolean, default=False)
    help_requested_at: Mapped[int | None] = mapped_column(BigInteger)
    help_resolved_at: Mapped[int | None] = mapped_column(BigInteger)
    cart: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)  # {lines, total, summary}
    order_id: Mapped[str | None] = mapped_column(String(36))
    submission: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    __mapper_args__ = {"version_id_col": version}


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
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
    accepted_at: Mapped[int | None] = mapped_column(BigInteger)
    preparing_at: Mapped[int | None] = mapped_column(BigInteger)
    ready_at: Mapped[int | None] = mapped_column(BigInteger)
    picked_up_at: Mapped[int | None] = mapped_column(BigInteger)
    cancelled_at: Mapped[int | None] = mapped_column(BigInteger)
    cancelled_by: Mapped[str | None] = mapped_column(String(16))
