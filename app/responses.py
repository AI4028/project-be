"""Response contracts shared by HTTP endpoints and live events."""
from typing import Any, Literal
from pydantic import ConfigDict
from app.schemas import CamelModel


class DeviceOut(CamelModel):
    device_id: str
    token: str


class Location(CamelModel):
    lat: float
    lng: float | None


class StoreOut(CamelModel):
    model_config = ConfigDict(extra='allow')
    store_id: str
    name: str
    name_en: str | None
    address: str | None
    location: Location | None
    geofence_radius_m: int | None
    ordering_methods: list[str]
    accessibility: dict[str, Any]
    kiosk_features: dict[str, Any]
    indoor_directions: str | None
    menu: list[dict[str, Any]] | None = None
    distance_m: int | None = None
    inside_geofence: bool | None = None


class KioskOut(CamelModel):
    kiosk_id: str
    store_id: str
    name: str | None
    name_en: str | None


class TokenOut(CamelModel):
    kiosk_id: str
    token: str
    expires_at_ms: int
    refresh_in_ms: int | None = None


class ChoiceOut(CamelModel):
    option_id: str
    option_name: str
    choice_id: str
    choice_name: str
    price_delta: int


class LineOut(CamelModel):
    item_id: str
    name: str
    name_en: str | None
    qty: int
    options: list[ChoiceOut]
    unit_price: int
    line_total: int


class CartOut(CamelModel):
    quote_id: str | None = None
    lines: list[LineOut]
    total: int
    summary: str


class SessionOut(CamelModel):
    session_id: str
    kiosk_id: str
    store_id: str
    status: Literal['active', 'ordered', 'ended', 'expired']
    help_requested: bool
    cart: CartOut
    order_id: str | None
    last_active_at_ms: int


OrderStatus = Literal['submitted', 'accepted', 'preparing', 'ready', 'picked_up', 'cancelled']


class OrderOut(CamelModel):
    order_id: str
    order_number: int
    kiosk_id: str
    session_id: str
    status: OrderStatus
    total: int
    summary: str
    lines: list[LineOut]
    note: str
    payment_method: Literal['counter', 'kiosk']
    created_at_ms: int
    updated_at_ms: int


class Event(CamelModel):
    kiosk_id: str
    session_id: str
    store_id: str
    at_ms: int


class Connected(Event):
    type: Literal['connected']
    kiosk_name: str
    store_name: str | None


class CartEvent(Event, CartOut):
    type: Literal['cart']


class Ordered(Event):
    type: Literal['ordered']
    order_id: str
    order_number: int
    total: int
    summary: str
    status: Literal['submitted']
    payment_method: Literal['counter', 'kiosk']
    note: str


class HelpEvent(Event):
    type: Literal['help', 'help_resolved']


class Ended(Event):
    type: Literal['ended']
    status: Literal['active', 'ordered', 'ended', 'expired']


class OrderEvent(Event):
    type: Literal['order_status']
    order_id: str
    order_number: int
    status: OrderStatus


class AvailabilityOut(CamelModel):
    item_id: str
    available: bool


class ProximityOut(CamelModel):
    status: Literal['ok']
    distance: float


class KioskState(CamelModel):
    session: SessionOut | None
    orders: list[OrderOut]
    store: StoreOut


class PhoneState(CamelModel):
    session: SessionOut
    order: OrderOut | None
    store: StoreOut
