"""Settings read from environment variables (or a local .env you load yourself)."""

from __future__ import annotations

import os

# Local development uses a SQLite file next to the project. On AWS, point this
# at PostgreSQL, e.g. postgresql+psycopg://user:password@host:5432/linkage
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./linkage.db")

# Pairing tokens the kiosk broadcasts over Bluetooth.
TOKEN_TTL_MS = 60_000  # a token is accepted for 60 s
TOKEN_REFRESH_MS = 30_000  # the kiosk gets a new one every 30 s
TOKEN_LENGTH = 8

# A phone connection ends after this much inactivity.
SESSION_IDLE_MS = 10 * 60_000

MAX_LINES_PER_ORDER = 20
MAX_QTY_PER_LINE = 10
MAX_NOTE_LENGTH = 200
PAYMENT_METHODS = ("counter", "kiosk")

# Order numbers restart every day at midnight Korea time.
KST_OFFSET_MS = 9 * 60 * 60_000

# Browser origins allowed to call the API, comma-separated ("*" = any).
# The web frontend lives in its own repo, so it calls from another origin.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# Optional: serve a built web frontend at /app from this folder.
FRONTEND_DIR = os.getenv("FRONTEND_DIR") or None

# Demo shortcuts for browsers that cannot read the kiosk's Bluetooth broadcast
# (see app/routers/demo.py). They let anyone get a kiosk's pairing token, so
# they are OFF unless DEMO_MODE=1. Never enable them on a real deployment.
DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
