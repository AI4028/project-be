"""Bounded, process-local throttling for the supported single-worker deployment.

Uses the socket peer, never untrusted forwarding headers. Configure trusted
proxy handling in the ASGI server when deploying behind a proxy.
"""
import time
from collections import OrderedDict, deque
from threading import Lock

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self, limit: int, window: int = 60, max_clients: int = 10000):
        self.limit = limit
        self.window = window
        self.max_clients = max_clients
        self.entries = OrderedDict()
        self.lock = Lock()

    def __call__(self, request: Request):
        key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self.lock:
            # Entries are ordered by last access; drop only expired clients.
            while self.entries and next(iter(self.entries.values()))[-1] <= now - self.window:
                self.entries.popitem(last=False)
            if key not in self.entries and len(self.entries) >= self.max_clients:
                raise HTTPException(429, "Too many clients; retry shortly.", headers={"Retry-After": str(self.window)})
            attempts = self.entries.setdefault(key, deque())
            while attempts and attempts[0] <= now - self.window:
                attempts.popleft()
            if len(attempts) >= self.limit:
                wait = max(1, int(attempts[0] + self.window - now) + 1)
                raise HTTPException(429, "Too many requests; retry shortly.", headers={"Retry-After": str(wait)})
            attempts.append(now)
            self.entries.move_to_end(key)


registration_limit = RateLimiter(30)
pairing_limit = RateLimiter(60)
