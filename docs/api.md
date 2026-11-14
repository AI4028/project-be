# API reference

Galjido serves store accessibility info and lets a phone pair with a kiosk,
build a cart, ask for help and place an order. Staff manage orders from the kiosk.

Local URL: `http://127.0.0.1:8000`. Try requests at `/docs`; `/redoc` and
`/openapi.json` are also available. Setup: [README](../README.md#quickstart).

JSON uses camelCase. Prices are whole Korean won; timestamps use Unix milliseconds.
Success is `200`, except registration, pairing and order submission (`201`).

## Auth

- **Public:** no token, including `POST /devices`.
- **Phone:** register once, save the token, then send `Authorization: Bearer dev_...`.
- **Kiosk:** send `Authorization: Bearer ksk_...`. Issue a key with `python -m scripts.create_kiosk GK01` after seeding. Running it again replaces the key.

The short Bluetooth pairing token is separate from these auth tokens.

## Public endpoints

Functions: [main.py](../app/main.py), [public.py](../app/routers/public.py).

| Endpoint | Function | What it does / returns |
| --- | --- | --- |
| `GET /` | `read_root` | `{"message":"Galjido API is running"}`. |
| `GET /health` | `health_check` | `{"status":"ok"}`. Does not check the database. |
| `GET /stores` | `list_stores` | All stores, sorted by name, without menus. |
| `GET /stores/nearby` | `nearby_stores` | Required `lat`, `lng`; optional `radiusM` (default 2000, range 1–20000). Stores without menus, nearest first, with `distanceM` and `insideGeofence`. |
| `GET /stores/{store_id}` | `get_store` | One store with accessibility info, ordering methods, kiosk features, indoor directions and full menu. |
| `GET /kiosks/{kiosk_id}` | `get_kiosk` | `kioskId`, `storeId`, `name`, `nameEn`. |

Nearby search accepts latitude −90 to 90 and longitude −180 to 180.
It uses the location sent by the client; it does not track the phone.

## Phone endpoints

Functions: [phone.py](../app/routers/phone.py). Phone auth required except registration.
“No body” means no JSON body is needed.

| Endpoint | Function | Input → result |
| --- | --- | --- |
| `POST /devices` | `register_device` | No body → anonymous `deviceId` and `token`; no sign-up. |
| `POST /sessions` | `connect` | `kioskId`, `token` → `connected` event with `sessionId`, store and kiosk details. |
| `GET /sessions/{session_id}` | `get_session` | No body → own session: status, cart, help flag, order ID and last activity time. |
| `PUT /sessions/{session_id}/cart` | `update_cart` | `items` → replaces the cart; returns `cart` event with priced `lines`, `total`, `summary`. `[]` clears it. |
| `POST /sessions/{session_id}/order` | `place_order` | `items`, optional `paymentMethod`, `note` → `ordered` event with `orderId`, `orderNumber`, total and status. Frees the kiosk. |
| `POST /sessions/{session_id}/help` | `ask_for_help` | No body → flags the session for staff; returns `help` event. |
| `POST /sessions/{session_id}/end` | `disconnect` | No body → disconnects; returns `ended` event. Does not cancel an order. |
| `GET /orders/{order_id}` | `get_order` | No body → own order: status, lines, total, summary, payment choice, note and timestamps. |
| `POST /orders/{order_id}/cancel` | `cancel_order` | No body → cancels a `submitted` order; returns `order_status` event. |

### Cart and order body

For an order, send the body below. For a cart update, send only `items`.
Item and option IDs come from the store's menu.

```json
{
  "items": [
    {"itemId": "americano", "qty": 1, "options": {"temp": "ice", "size": "large", "extra": ["shot"]}}
  ],
  "paymentMethod": "counter",
  "note": ""
}
```

- The server calculates prices and checks stock/options. Maximum 20 lines, quantity 1–10 per line. Orders cannot be empty.
- Single-choice options take a string; multi-choice options take an array. Include every required option.
- `paymentMethod`: `counter` (default) or `kiosk`. Records where to pay; it does not charge anyone. `note`: up to 200 characters, default empty.
- Order numbers start at 1 per store and reset at midnight KST. Submission sets the session to `ordered`; pair again for another order.

## Kiosk endpoints

Functions: [kiosk.py](../app/routers/kiosk.py). Kiosk auth required.

| Endpoint | Function | Input → result |
| --- | --- | --- |
| `POST /kiosk/heartbeat` | `heartbeat` | No body → `kioskId`, pairing `token`, `expiresAtMs`, `refreshInMs`. Call again after `refreshInMs`. |
| `GET /kiosk/session` | `active_session` | No body → active phone session and cart, or `null`. |
| `GET /kiosk/orders` | `todays_orders` | Optional `?status=submitted` → today's orders for the kiosk's **store**, newest first. |
| `POST /kiosk/orders/{order_id}/status` | `set_order_status` | `{"status":"accepted"}` → updates an order in this store; returns `order_status` event. |
| `POST /kiosk/sessions/{session_id}/resolve-help` | `help_handled` | No body → clears this kiosk's help request; returns `help_resolved` event. |
| `POST /kiosk/sessions/{session_id}/end` | `end_phone_session` | No body → disconnects this kiosk's phone; returns `ended` event. |
| `PUT /kiosk/menu/{item_id}/availability` | `set_availability` | `{"available":false}` → marks an item sold out; returns `itemId`, `available`. `true` restores it. |

Order flow: `submitted → accepted → preparing → ready → picked_up`.
Staff can cancel from `submitted` or `accepted`; the phone can cancel only from
`submitted`. Skipping steps returns `bad-transition`.

## Bluetooth advertisement

Intended payload: `LK` + four-character kiosk ID + eight-character token,
e.g. `LKGK017H3KQ9ZC`. Split into `kioskId` and `token` for pairing.
The Arduino prototype does not send this yet: [hardware gaps](hardware.md#known-gaps).

Tokens rotate about every 30 seconds and expire after 60 seconds. The previous
token works until its original expiry. One phone per kiosk; the same phone can
reconnect to its active session.

Sessions become unusable after 10 minutes without activity. Reads and socket
pings do not refresh activity. Expiry is checked on requests, with no automatic
`ended` event; a session read can still show the stored `active` status.

## Live updates

Functions: [ws.py](../app/routers/ws.py). Use `ws://` locally, `wss://` with HTTPS.

| WebSocket path | Function | Listener |
| --- | --- | --- |
| `/ws/kiosk?token=ksk_...` | `kiosk_events` | The authenticated kiosk. |
| `/ws/sessions/{session_id}?token=dev_...` | `session_events` | The session's phone, including after ordering. |

Session/order mutations return an event over HTTP and publish it to the related
kiosk and session sockets. Events contain `type`, `kioskId`, `sessionId`,
`storeId`, `atMs`, plus these fields:

| Event | Extra fields |
| --- | --- |
| `connected` | `kioskName`, `storeName` |
| `cart` | `lines`, `total`, `summary` |
| `ordered` | `orderId`, `orderNumber`, `total`, `summary`, `status`, `paymentMethod`, `note` |
| `help`, `help_resolved` | None |
| `order_status` | `orderId`, `orderNumber`, `status` |
| `ended` | Session `status` |

Sockets send future events only. After connecting/reconnecting, fetch current
state through HTTP. Client messages are ignored. Stock changes have no event;
refetch the menu. Rejections use `4401` (bad token) or `4403` (missing session
or wrong owner).

## Demo endpoints

Functions: [demo.py](../app/routers/demo.py). No auth. Disabled unless `DEMO_MODE=1`:
HTTP returns `404` / `demo-disabled`; the socket uses `4404`. Keep off in production.

| Endpoint | Function | Input → result |
| --- | --- | --- |
| `GET /kiosks/{kiosk_id}/token` | `get_kiosk_token` | `kioskId`, `token`, `expiresAtMs`; creates a fresh token if needed. Allows pairing without Bluetooth. |
| `POST /proximity` | `report_proximity` | Required `distance`; optional `storeName` (default `GIST Cafe점`), `kioskId` (`GK01`), `rssi` (`null`) → broadcasts a reading; returns `status`, `distance`. |
| `WS /ws/proximity` | `proximity_events` | Receives `{"type":"proximity", ...readingFields}`. Readings are not saved. |

## Common errors

Application errors use `{"error":"code","message":"English explanation"}`.
Request validation errors also include `details`. Map codes to accessible Korean
messages. Unknown routes use FastAPI's default error format.

| HTTP | Codes | What to do |
| --- | --- | --- |
| 400 | `bad-request`, `bad-kiosk-id`, `bad-token`, `bad-qty`, `missing-option`, `bad-payment-method`, `bad-note` | Fix the request or menu selections. |
| 401 | `not-signed-in`, `not-kiosk` | Supply the correct phone token or kiosk key. |
| 403 | `token-invalid`, `not-your-session` | Rescan an expired pairing token, or use your own session. |
| 404 | `store-not-found`, `kiosk-not-found`, `session-not-found`, `order-not-found`, `unknown-item` | Check the ID. Reads also hide sessions/orders belonging to another caller. |
| 409 | `kiosk-busy`, `session-expired` | Wait for the kiosk or pair again. |
| 409 | `item-unavailable`, `choice-unavailable`, `too-late-to-cancel`, `bad-transition` | Refresh the menu or order and show the reason. |

Full rules: [logic.py](../app/logic.py). Error mapping: [errors.py](../app/errors.py).

## Running it

- SQLite locally; set `DATABASE_URL` for Postgres and `CORS_ORIGINS` for allowed browser origins.
- Startup creates missing tables; it does not migrate existing schemas.
- Run one server process: WebSocket subscriptions are held in memory.
- Settings come from environment variables. `.env` is not loaded automatically.
- Optional `FRONTEND_DIR` serves a built frontend at `/app`.

Next steps: [roadmap](roadmap.md).
