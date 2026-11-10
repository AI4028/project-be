# Galjido Backend

FastAPI backend for Galjido (갈지도): accessible store info and phone-based kiosk ordering.

A phone finds a kiosk over Bluetooth, pairs with it, and orders from an
accessible phone screen. The kiosk shows the cart and the order live.

## Quickstart

Python 3.10+. Windows PowerShell, from the repo folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m scripts.seed seed\gist-cafe.json
.\.venv\Scripts\python.exe -m scripts.create_kiosk GK01
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- `scripts.seed` loads the demo cafe (menu, accessibility info, kiosk GK01).
- `scripts.create_kiosk` prints the kiosk key once. Save it.
- Data lives in `galjido.db` (SQLite). Delete it to start over.

Open http://127.0.0.1:8000/docs to try every endpoint.

Tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

CI also runs them on Postgres. Locally, with Docker:

```powershell
docker run -d --name galjido-pg -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=galjido_test -p 5432:5432 postgres:17
$env:TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@127.0.0.1:5432/galjido_test"
.\.venv\Scripts\python.exe -m pytest
```

## How it works

1. The kiosk calls `POST /kiosk/heartbeat` every ~30 s and broadcasts the token over Bluetooth. Tokens expire after 60 s.
2. The phone hears it and calls `POST /sessions`. Only a phone at the kiosk knows a fresh token.
3. The phone sends its cart. The server prices it from the real menu and the kiosk updates live.
4. The phone places the order and gets a daily number (#1, #2, ... reset at midnight KST).
5. Staff move it through `accepted → preparing → ready → picked_up`. The phone hears each step.

## Structure

```text
app/          FastAPI app
  routers/    public, phone, kiosk, ws, demo
scripts/      seed data, issue kiosk keys
seed/         demo store (JSON)
hardware/     Arduino Bluetooth beacon + serial bridge
tests/        pytest
docs/         overview, map, hardware, API, roadmap
```

The web frontend lives in its own repo and calls this API cross-origin (`CORS_ORIGINS`).

## Demo mode

Browsers can't read the kiosk's Bluetooth broadcast, so demo mode adds shortcuts
(`GET /kiosks/{id}/token`, `POST /proximity`, `ws://HOST/ws/proximity`).
They let anyone pair remotely, so they are off unless:

```powershell
$env:DEMO_MODE = "1"; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0
```

Never enable demo mode on a real deployment.

Arduino beacon setup: [docs/hardware.md](docs/hardware.md).

## Docs

- [Overview](docs/overview.md)
- [Map](docs/map.md)
- [Hardware](docs/hardware.md)
- [API reference](docs/api.md)
- [Roadmap](docs/roadmap.md)
- [Contributing](CONTRIBUTING.md)

Settings come from environment variables. See [.env.example](.env.example).
