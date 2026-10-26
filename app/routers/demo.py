"""Demo shortcuts for the web prototype and the Arduino beacon. OFF unless DEMO_MODE=1.

A web browser usually cannot read the kiosk's Bluetooth broadcast (no Web
Bluetooth on iPhones), so for demos it can:

- ask the server for the kiosk's current pairing token
  (GET /kiosks/{id}/token), and
- get distance readings from the Arduino beacon, which hardware/bt_bridge.py
  posts to POST /proximity and the server forwards to /ws/proximity.

The token shortcut skips the "phone must be at the kiosk" check that pairing
is built on, so these routes answer 404 (and the WebSocket closes) unless
DEMO_MODE is on.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, WebSocket
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import config, service
from app.clock import get_now
from app.db import get_db
from app.errors import AppError
from app.models import Kiosk
from app.realtime import hub
from app.routers.ws import _listen

router = APIRouter(tags=["demo"])

DISABLED = 4404  # WebSocket close code when demo mode is off


def require_demo_mode() -> None:
    if not config.DEMO_MODE:
        raise AppError("demo-disabled", "Demo endpoints are off. Start the server with DEMO_MODE=1.")


class ProximityIn(BaseModel):
    distance: float
    storeName: str = "GIST Cafe점"
    kioskId: str = "GK01"
    rssi: Optional[int] = None


@router.get("/kiosks/{kiosk_id}/token", dependencies=[Depends(require_demo_mode)])
def get_kiosk_token(kiosk_id: str, db: Session = Depends(get_db), now: int = Depends(get_now)) -> dict[str, Any]:
    """The kiosk's current Bluetooth pairing token, as if the phone had heard it."""
    kiosk = db.get(Kiosk, kiosk_id)
    if kiosk is None:
        raise AppError("kiosk-not-found", "Kiosk not found.")
    if not kiosk.current_token or not kiosk.current_expires_at or kiosk.current_expires_at <= now:
        # No kiosk app is running: rotate the token on its behalf.
        service.kiosk_heartbeat(db, kiosk, now, mark_seen=False)
    return {"kioskId": kiosk.id, "token": kiosk.current_token, "expiresAtMs": kiosk.current_expires_at}


@router.post("/proximity", dependencies=[Depends(require_demo_mode)])
async def report_proximity(body: ProximityIn) -> dict[str, Any]:
    """The Bluetooth bridge reports how far the phone is from the beacon."""
    await hub.send("proximity", {"type": "proximity", **body.model_dump()})
    return {"status": "ok", "distance": body.distance}


@router.websocket("/ws/proximity")
async def proximity_events(ws: WebSocket) -> None:
    if not config.DEMO_MODE:
        await ws.close(code=DISABLED)
        return
    await _listen(ws, "proximity")
