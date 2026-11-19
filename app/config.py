"""Settings, read from environment variables."""

import os

# SQLite locally. In production, e.g. postgresql+psycopg://user:password@host:5432/galjido
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./galjido.db")

# Bluetooth pairing tokens.
TOKEN_TTL_MS = 60_000
TOKEN_REFRESH_MS = 30_000
TOKEN_LENGTH = 8

# A phone connection ends after this much inactivity.
SESSION_IDLE_MS = 10 * 60_000

MAX_LINES_PER_ORDER = 20
MAX_QTY_PER_LINE = 10
MAX_NOTE_LENGTH = 200
PAYMENT_METHODS = ("counter", "kiosk")

# Order numbers restart daily at midnight KST.
KST_OFFSET_MS = 9 * 60 * 60_000

# Comma-separated browser origins ("*" = any). The frontend is served from its own repo.
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]

# Optional: serve a built frontend at /app.
FRONTEND_DIR = os.getenv("FRONTEND_DIR") or None

# Demo shortcuts (app/routers/demo.py) let anyone pair with a kiosk remotely.
# Never enable on a real deployment.
DEMO_MODE = os.getenv("DEMO_MODE", "").lower() in ("1", "true", "yes")
