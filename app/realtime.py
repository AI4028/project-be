"""Live updates over WebSockets.

The kiosk listens on /ws/kiosk and each phone on /ws/sessions/{id}. Every
event (phone connected, cart changed, order placed, help requested, order
status changed, session ended) is sent to both the kiosk and the phone.

Note: connections live in this process's memory, so run ONE server process
(uvicorn without --workers). Several processes would need a shared message
broker such as Redis; not needed for the pilot.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class Hub:
    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = defaultdict(set)

    def join(self, channel: str, ws: WebSocket) -> None:
        self._channels[channel].add(ws)

    def leave(self, channel: str, ws: WebSocket) -> None:
        self._channels[channel].discard(ws)
        if not self._channels[channel]:
            self._channels.pop(channel, None)

    async def send(self, channel: str, message: dict[str, Any]) -> None:
        for ws in list(self._channels.get(channel, ())):
            try:
                await ws.send_json(message)
            except Exception:  # connection already closed
                self.leave(channel, ws)

    async def publish(self, event: dict[str, Any]) -> None:
        """Send an event to its kiosk and to the phone in its session."""
        await self.send(f"kiosk:{event['kioskId']}", event)
        if event.get("sessionId"):
            await self.send(f"session:{event['sessionId']}", event)


hub = Hub()
