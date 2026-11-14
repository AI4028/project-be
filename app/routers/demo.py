"""Demo shortcuts for browsers that can't read the kiosk's Bluetooth broadcast.

- GET /kiosks/{id}/token: the current pairing token, as if heard over Bluetooth.
- POST /proximity -> /ws/proximity: beacon distances from hardware/bt_bridge.py.

The token route skips the "phone is at the kiosk" proof, so everything here
is 404 (WebSocket closes 4404) unless DEMO_MODE=1.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, WebSocket
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.responses import ProximityOut, TokenOut
from app import config, service
from app.clock import get_now
from app.db import get_db
from app.errors import AppError
from app.models import Kiosk
from app.realtime import hub
from app.routers.ws import listen

router = APIRouter(tags=["demo"])

DISABLED = 4404  # WebSocket close code when DEMO_MODE is off


def require_demo_mode() -> None:
    if not config.DEMO_MODE:
        raise AppError("demo-disabled", "Demo endpoints are off. Start the server with DEMO_MODE=1.")


class ProximityIn(BaseModel):
    distance: float
    storeName: str = "GIST Cafe점"
    kioskId: str = "GK01"
    rssi: int | None = None


@router.get("/kiosks/{kiosk_id}/token", dependencies=[Depends(require_demo_mode)], response_model=TokenOut, response_model_exclude_unset=True)
def get_kiosk_token(kiosk_id: str, db: Session = Depends(get_db), now: int = Depends(get_now)) -> dict[str, Any]:
    """The kiosk's current Bluetooth pairing token, as if the phone had heard it."""
    kiosk = db.get(Kiosk, kiosk_id)
    if kiosk is None:
        raise AppError("kiosk-not-found", "Kiosk not found.")
    if not kiosk.current_token or not kiosk.current_expires_at or kiosk.current_expires_at <= now:
        # No kiosk app running: rotate on its behalf.
        service.kiosk_heartbeat(db, kiosk, now, mark_seen=False)
    return {"kioskId": kiosk.id, "token": kiosk.current_token, "expiresAtMs": kiosk.current_expires_at}


@router.post("/proximity", dependencies=[Depends(require_demo_mode)], response_model=ProximityOut, response_model_exclude_unset=True)
async def report_proximity(body: ProximityIn) -> dict[str, Any]:
    """A beacon distance reading from the Bluetooth bridge."""
    await hub.send("proximity", {"type": "proximity", **body.model_dump()})
    return {"status": "ok", "distance": body.distance}


@router.websocket("/ws/proximity")
async def proximity_events(ws: WebSocket) -> None:
    if not config.DEMO_MODE:
        await ws.close(code=DISABLED)
        return
    await listen(ws, "proximity")
