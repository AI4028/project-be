"""The current time, as a FastAPI dependency so tests can control it."""

from __future__ import annotations

import time


def now_ms() -> int:
    return int(time.time() * 1000)


def get_now() -> int:
    return now_ms()
