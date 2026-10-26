"""WebSocket endpoints for live updates.

Browsers and phones can't set headers on WebSockets, so the token goes in
the URL:  ws://HOST/ws/kiosk?token=ksk_...
          ws://HOST/ws/sessions/<sessionId>?token=dev_...
Messages are JSON events, e.g. {"type": "cart", "kioskId": "GK01", ...}.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.auth import device_for_token, kiosk_for_key
from app.db import get_db
from app.models import KioskSession
from app.realtime import hub

router = APIRouter(tags=["live updates"])

# Close codes the apps can check (4000-4999 are free for applications).
UNAUTHORIZED = 4401
FORBIDDEN = 4403


async def _listen(ws: WebSocket, channel: str) -> None:
    await ws.accept()
    hub.join(channel, ws)
    try:
        while True:
            await ws.receive_text()  # the app may send pings; nothing to do
    except WebSocketDisconnect:
        pass
    finally:
        hub.leave(channel, ws)


@router.websocket("/ws/kiosk")
async def kiosk_events(ws: WebSocket, token: str = "", db: Session = Depends(get_db)) -> None:
    kiosk = kiosk_for_key(db, token)
    if kiosk is None:
        await ws.close(code=UNAUTHORIZED)
        return
    channel = f"kiosk:{kiosk.id}"
    db.close()  # don't hold a database connection while the socket is open
    await _listen(ws, channel)


@router.websocket("/ws/sessions/{session_id}")
async def session_events(ws: WebSocket, session_id: str, token: str = "", db: Session = Depends(get_db)) -> None:
    device = device_for_token(db, token)
    if device is None:
        await ws.close(code=UNAUTHORIZED)
        return
    session = db.get(KioskSession, session_id)
    if session is None or session.device_id != device.id:
        await ws.close(code=FORBIDDEN)
        return
    db.close()
    await _listen(ws, f"session:{session_id}")
