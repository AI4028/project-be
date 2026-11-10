# API Reference

JSON uses camelCase. The live, clickable list is at `/docs` on a running server.

## Auth

- **Phone:** on first launch call `POST /devices` → `{"deviceId", "token"}`.
  Store the token (Keychain) and send `Authorization: Bearer dev_...`. No sign-up.
- **Kiosk:** send `Authorization: Bearer ksk_...` (from `scripts.create_kiosk`).

## Bluetooth advertisement

The kiosk broadcasts `"LK" + kioskId (4 chars) + token (8 chars)`, e.g.
`LKGK017H3KQ9ZC`. The phone strips `LK`, splits the rest, and calls
`POST /sessions`. The exact BLE field depends on the kiosk device (iPad or
Android); not decided yet.

## Public

| Method and path | What it does |
| --- | --- |
| `GET /stores` | All stores |
| `GET /stores/{id}` | Store info, accessibility, menu |
| `GET /stores/nearby?lat=&lng=&radiusM=` | Stores within `radiusM` (default 2000), nearest first, with `distanceM` and `insideGeofence` |
| `GET /kiosks/{id}` | Kiosk info |

## Phone

| Method and path | Body | What it does |
| --- | --- | --- |
| `POST /devices` | — | Get an anonymous device token |
| `POST /sessions` | `kioskId`, `token` | Connect to a kiosk → `sessionId` |
| `GET /sessions/{id}` | — | Connection status and cart |
| `PUT /sessions/{id}/cart` | `items` | Update the cart shown on the kiosk |
| `POST /sessions/{id}/order` | `items`, `paymentMethod`?, `note`? | Place the order → `orderId`, `orderNumber` |
| `POST /sessions/{id}/help` | — | Ask staff for help |
| `POST /sessions/{id}/end` | — | Disconnect |
| `GET /orders/{id}` | — | Order status |
| `POST /orders/{id}/cancel` | — | Cancel before staff accepts |

`items` (prices are never sent; the server computes them):

```json
[{"itemId": "americano", "qty": 1, "options": {"temp": "ice", "size": "large", "extra": ["shot"]}}]
```

`paymentMethod` is `counter` (default) or `kiosk`. One phone per kiosk at a
time. A phone idle for 10 minutes is disconnected.

## Kiosk

| Method and path | Body | What it does |
| --- | --- | --- |
| `POST /kiosk/heartbeat` | — | Get the Bluetooth token. Call again after `refreshInMs` |
| `GET /kiosk/session` | — | The connected phone and its cart, or `null` |
| `GET /kiosk/orders?status=` | — | Today's orders, newest first |
| `POST /kiosk/orders/{id}/status` | `status` | `accepted`, `preparing`, `ready`, `picked_up`, `cancelled` |
| `POST /kiosk/sessions/{id}/resolve-help` | — | Staff handled the help request |
| `POST /kiosk/sessions/{id}/end` | — | Disconnect the phone |
| `PUT /kiosk/menu/{itemId}/availability` | `available` | Sold out / back in stock |

## Live updates (WebSocket)

- Kiosk: `ws://HOST/ws/kiosk?token=ksk_...`
- Phone: `ws://HOST/ws/sessions/{sessionId}?token=dev_...`

Each message is a JSON event with a `type`: `connected`, `cart`, `ordered`,
`help`, `help_resolved`, `order_status`, `ended`. The kiosk and the phone in
that session both get every event. Refused connections close with `4401`
(bad token) or `4403` (not your session).

## Demo mode

Off (404, WebSocket closes with `4404`) unless `DEMO_MODE=1`. Never on a real deployment.

| Method and path | What it does |
| --- | --- |
| `GET /kiosks/{id}/token` | The kiosk's current pairing token, as if heard over Bluetooth |
| `POST /proximity` | `distance`, `storeName`?, `kioskId`?, `rssi`?: a beacon reading |
| `ws://HOST/ws/proximity` | Every proximity reading, live |

## Errors

Every error is `{"error": "<code>", "message": "..."}`. Map codes to Korean
messages the screen reader can read.

| Code | HTTP | Meaning |
| --- | --- | --- |
| `token-invalid` | 403 | Too far or token expired: move closer and rescan |
| `kiosk-busy` | 409 | Another phone is using this kiosk |
| `session-expired`, `session-not-found` | 409, 404 | Connection ended: reconnect |
| `item-unavailable`, `choice-unavailable` | 409 | Sold out |
| `missing-option` | 400 | A required option (e.g. size) was not chosen |
| `too-late-to-cancel` | 409 | Staff already started the order |
| `not-signed-in`, `not-kiosk` | 401 | Missing or wrong token |
| `not-your-session`, `not-your-kiosk` | 403 | Token belongs to someone else |
| `bad-request`, `bad-qty`, `unknown-item`, ... | 400, 404 | App bug: invalid request |

## Deploying

- Use Postgres: `DATABASE_URL=postgresql+psycopg://user:password@host:5432/galjido`.
  Tables are created on first start. Then load the store and issue kiosk keys
  with `scripts.seed` and `scripts.create_kiosk`, as in the quickstart.
- Schema changes are not migrated: the app only creates missing tables. Until
  there is data worth keeping, drop the tables and reseed.
- Run **one** server process (no `--workers`): live updates are kept in memory.
  Use a host with WebSocket support (e.g. AWS EC2 or Lightsail).
- Keep secrets in a local `.env`. It is ignored by Git.
