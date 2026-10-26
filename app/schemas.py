"""Request bodies. JSON uses camelCase (e.g. "kioskId") to match the apps."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ConnectIn(CamelModel):
    kiosk_id: str
    token: str


class CartIn(CamelModel):
    # [{"itemId": "americano", "qty": 1, "options": {"temp": "ice", "extra": ["shot"]}}]
    # Checked in app/logic.py so errors come back with specific codes.
    items: list[Any]


class OrderIn(CamelModel):
    items: list[Any]
    payment_method: str = "counter"  # counter | kiosk
    note: str = ""


class StatusIn(CamelModel):
    status: str  # accepted | preparing | ready | picked_up | cancelled


class AvailabilityIn(CamelModel):
    available: bool
