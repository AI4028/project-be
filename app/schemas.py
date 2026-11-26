"""Request bodies, camelCase on the wire."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class ConnectIn(CamelModel):
    kiosk_id: str
    token: str


class CartIn(CamelModel):
    items: list[Any]  # validated in logic.build_order_lines for specific error codes


DiningOption = Literal["dine_in", "takeaway"]


class OrderIn(CamelModel):
    items: list[Any]
    quote_id: str | None = None
    simulate_payment: bool = False
    payment_method: str = "counter"
    dining_option: DiningOption | None = None
    note: str = ""


class StatusIn(CamelModel):
    status: str  # accepted | preparing | ready | picked_up | cancelled


class OrderingIn(CamelModel):
    paused: bool


class AvailabilityIn(CamelModel):
    available: bool
