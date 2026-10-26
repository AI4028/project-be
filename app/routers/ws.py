"""WebSocket endpoints for live updates.

Browsers and phones can't set headers on WebSockets, so the token goes in
the URL:  ws://HOST/ws/kiosk?token=ksk_...
          ws://HOST/ws/sessions/<sessionId>?token=dev_...
Messages are JSON events, e.g. {"type": "cart", "kioskId": "GK01", ...}.
"""

from __future__ import annotations

from typing import Optional, Union

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app import db as database
from app.auth import device_for_token, kiosk_for_key
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


# The token checks below use the database, which blocks. They run in a worker
# thread: on the event loop, waiting for SQLite's lock would freeze the whole
# server, including the request that holds the lock and needs the loop to finish.


def _kiosk_channel(token: str) -> Optional[str]:
    with database.SessionLocal() as db:
        kiosk = kiosk_for_key(db, token)
        return f"kiosk:{kiosk.id}" if kiosk else None


def _session_channel(session_id: str, token: str) -> Union[str, int]:
    """The channel to listen on, or the close code if refused."""
    with database.SessionLocal() as db:
        device = device_for_token(db, token)
        if device is None:
            return UNAUTHORIZED
        session = db.get(KioskSession, session_id)
        if session is None or session.device_id != device.id:
            return FORBIDDEN
        return f"session:{session_id}"


@router.websocket("/ws/kiosk")
async def kiosk_events(ws: WebSocket, token: str = "") -> None:
    channel = await run_in_threadpool(_kiosk_channel, token)
    if channel is None:
        await ws.close(code=UNAUTHORIZED)
        return
    await _listen(ws, channel)


@router.websocket("/ws/sessions/{session_id}")
async def session_events(ws: WebSocket, session_id: str, token: str = "") -> None:
    channel = await run_in_threadpool(_session_channel, session_id, token)
    if isinstance(channel, int):
        await ws.close(code=channel)
        return
    await _listen(ws, channel)
