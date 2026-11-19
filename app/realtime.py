"""In-memory WebSocket hub: every event goes to the kiosk and the session's phone.

Connections live in this process, so run a single server process (no --workers).
Scaling out would need a broker such as Redis.
"""

from __future__ import annotations

from collections import defaultdict
import asyncio
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
                await asyncio.wait_for(ws.send_json(message), timeout=5)
            except Exception:  # connection already closed
                self.leave(channel, ws)

    async def publish(self, event: dict[str, Any]) -> None:
        """Send paired events to the kiosk and direct orders to store staff."""
        order_help = event.get("orderId") and event["type"] in {"help", "help_resolved"}
        direct_staff_update = event["kioskId"] is None and event["type"] in {
            "ordered", "order_status", "help", "help_resolved",
        }
        if order_help or direct_staff_update:
            await self.send(f"staff-store:{event['storeId']}", event)
        elif event["kioskId"] is not None:
            await self.send(f"kiosk:{event['kioskId']}", event)
        if event.get("sessionId"):
            await self.send(f"session:{event['sessionId']}", event)

    async def close(self, channel: str) -> None:
        for ws in list(self._channels.get(channel, ())):
            try:
                await ws.close(code=4401)
            except Exception:
                pass  # Already disconnected; still remove its subscription.
            finally:
                self.leave(channel, ws)


hub = Hub()
