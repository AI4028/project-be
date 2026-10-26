# Project Backend

FastAPI backend for accessible kiosk ordering. A phone finds a kiosk over
Bluetooth, connects to it, and orders from an accessible phone screen; the
kiosk shows the cart and the order live. Requires Python 3.10 or newer.

## Run locally (Windows PowerShell)

From the repository folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m scripts.seed seed\gist-cafe.json
.\.venv\Scripts\python.exe -m scripts.create_kiosk GK01
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

- `scripts.seed` loads the demo cafe (menu, accessibility info, kiosk GK01).
- `scripts.create_kiosk` prints the kiosk's secret key **once**; save it for the kiosk app.
- Data is stored in `linkage.db` (SQLite) in the project folder. Delete it to start over.

Using the virtual environment Python directly does not require activating it.
In VS Code, select `.venv\Scripts\python.exe` as your Python interpreter.

- App: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/health
- Interactive API documentation: http://127.0.0.1:8000/docs (try every endpoint here)

Run the tests:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## How it works

```text
Phone app  --Bluetooth-->  Kiosk app (broadcasts kiosk ID + pairing token)
    |                          |
    |  HTTP + WebSocket        |  HTTP + WebSocket
    v                          v
            FastAPI backend  -->  database
```

1. The kiosk calls `POST /kiosk/heartbeat` every ~30 s and broadcasts the
   returned token over Bluetooth. Tokens expire after 60 s.
2. The phone hears it and calls `POST /sessions` with the kiosk ID and token.
   Only a phone standing at the kiosk can know a current token. One phone per
   kiosk at a time; a phone idle for 10 minutes is disconnected.
3. The phone sends its cart (`PUT /sessions/{id}/cart`); the server prices it
   from the real menu and the kiosk screen updates live.
4. The phone places the order; it gets a number (#1, #2… restarting daily,
   Korea time) and appears on the kiosk.
5. Staff move it through `accepted → preparing → ready → picked_up`; the phone
   is told at each step.

## Structure

```text
app/
  main.py          # Application, routers, root and health routes
  config.py        # Settings (DATABASE_URL, timeouts, limits)
  db.py            # Database connection
  models.py        # Tables: stores, kiosks, devices, sessions, orders
  logic.py         # Pure rules: pricing, tokens, order status (no database)
  service.py       # Ordering logic using the database
  auth.py          # Phone device tokens and kiosk keys
  realtime.py      # Live updates to connected WebSockets
  schemas.py       # Request bodies
  errors.py        # Error codes and JSON error format
  routers/
    public.py      # GET /stores, /stores/{id}, /kiosks/{id}
    phone.py       # Phone app endpoints
    kiosk.py       # Kiosk app endpoints
    ws.py          # WebSocket live updates
scripts/
  seed.py          # Load a store from a JSON file
  create_kiosk.py  # Issue a kiosk key
seed/gist-cafe.json  # Demo cafe (placeholder prices and accessibility info)
tests/             # pytest: rules and full API flow
requirements.txt   # Runtime dependencies
requirements-dev.txt  # + test tools
```

## API for the apps

JSON uses camelCase. Full, clickable list at `/docs`.

### Who is calling

- **Phone:** on first launch call `POST /devices` → `{"deviceId", "token"}`. Store
  the token (Keychain) and send `Authorization: Bearer dev_...` on every call.
  No sign-up.
- **Kiosk:** send `Authorization: Bearer ksk_...` (from `scripts.create_kiosk`).

### Bluetooth advertisement (kiosk → phone)

The kiosk broadcasts `"LK" + kioskId (4 chars) + token (8 chars)`, e.g.
`LKGK017H3KQ9ZC`. The phone strips `LK`, splits the rest into kiosk ID and
token, and calls `POST /sessions`. (The exact BLE field depends on whether the
kiosk is an iPad or an Android tablet; to be decided with the app team.)

### Phone endpoints

| Method and path | Body | What it does |
| --- | --- | --- |
| `POST /devices` | — | Get an anonymous device token |
| `GET /stores`, `GET /stores/{id}` | — | Store info, accessibility, menu |
| `POST /sessions` | `kioskId`, `token` | Connect to a kiosk → `sessionId` |
| `GET /sessions/{id}` | — | Connection status and cart |
| `PUT /sessions/{id}/cart` | `items` | Update the cart shown on the kiosk |
| `POST /sessions/{id}/order` | `items`, `paymentMethod`?, `note`? | Place the order → `orderId`, `orderNumber` |
| `POST /sessions/{id}/help` | — | Ask staff for help |
| `POST /sessions/{id}/end` | — | Disconnect |
| `GET /orders/{id}` | — | Order status |
| `POST /orders/{id}/cancel` | — | Cancel before staff accepts |

`items` example (prices are never sent; the server computes them):

```json
[{"itemId": "americano", "qty": 1, "options": {"temp": "ice", "size": "large", "extra": ["shot"]}}]
```

`paymentMethod` is `counter` (default) or `kiosk`: payment happens there.

### Kiosk endpoints

| Method and path | Body | What it does |
| --- | --- | --- |
| `POST /kiosk/heartbeat` | — | Get the Bluetooth token; call again after `refreshInMs` |
| `GET /kiosk/session` | — | The connected phone and its cart, or `null` |
| `GET /kiosk/orders?status=` | — | Today's orders, newest first |
| `POST /kiosk/orders/{id}/status` | `status` | `accepted`, `preparing`, `ready`, `picked_up`, `cancelled` |
| `POST /kiosk/sessions/{id}/resolve-help` | — | Staff handled the help request |
| `POST /kiosk/sessions/{id}/end` | — | Disconnect the phone |
| `PUT /kiosk/menu/{itemId}/availability` | `available` | Mark sold out / back in stock |

### Live updates (WebSocket)

- Kiosk: `ws://HOST/ws/kiosk?token=ksk_...`
- Phone: `ws://HOST/ws/sessions/{sessionId}?token=dev_...`

Each message is a JSON event with a `type`: `connected`, `cart`, `ordered`,
`help`, `help_resolved`, `order_status`, `ended`. Both the kiosk and the phone
in that session receive every event. A refused connection closes with code
4401 (bad token) or 4403 (not your session).

### Errors

Every error is `{"error": "<code>", "message": "..."}`. Map codes to Korean
messages the screen reader can read:

| Code | HTTP | Meaning |
| --- | --- | --- |
| `token-invalid` | 403 | Too far from the kiosk or token expired: move closer and rescan |
| `kiosk-busy` | 409 | Another phone is using this kiosk |
| `session-expired`, `session-not-found` | 409, 404 | Connection ended: reconnect |
| `item-unavailable`, `choice-unavailable` | 409 | Sold out |
| `missing-option` | 400 | A required option (e.g. size) was not chosen |
| `too-late-to-cancel` | 409 | Staff already started the order |
| `not-signed-in`, `not-kiosk` | 401 | Missing or wrong token |
| `bad-request`, `bad-qty`, `unknown-item`, … | 400, 404 | App bug: invalid request |

## Deploying (later)

- Set `DATABASE_URL` to PostgreSQL (e.g. AWS RDS) and add a driver such as
  `psycopg[binary]` to `requirements.txt`. The code works unchanged.
- Run **one** server process (no `--workers`), because live updates are kept
  in memory. Use a host that supports WebSockets (e.g. AWS EC2, Lightsail, or
  Elastic Beanstalk).

Keep secrets in a local `.env` file; it is ignored by Git.

# Git merge convention

want to work on a specific feature: create a feature/(name of the feature) branch (from branch develop):
```
git checkout -b feature/(name of the feature)
```

finished working, merge to develop:
```
git checkout develop
git merge feature/(name of the feature)
```

merging into main is only after develop passess all the checks:
```
git checkout main
git merge develop
```
