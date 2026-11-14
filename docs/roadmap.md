# What we should work on

The backend has store lookup, nearby search, anonymous phone auth, pairing,
cart pricing, orders, staff help, stock toggles and live updates. Tests cover
the core flow; CI is configured for SQLite and Postgres.

This list is based on this repo. Frontend completion still needs checking
in its own repo.

## Before the pilot

| Priority | Task | Why / done when |
| --- | --- | --- |
| 1 | Fix the beacon → bridge format. | The sketch sends `STORE/KIOSK/TX/SEQ`; the bridge requires `DIST`, so it drops every current packet. Agree on the format and verify readings reach `/ws/proximity`. [Hardware](hardware.md#known-gaps) |
| 2 | Finish real Bluetooth pairing. | The beacon does not send the rotating API token. Connect heartbeat → broadcast → phone scan → `POST /sessions`, and test on target phones with demo mode off. |
| 3 | Replace the demo cafe data. | Prices, location and accessibility values are placeholders. Visit the store and update [gist-cafe.json](../seed/gist-cafe.json), including indoor directions. |
| 4 | Verify the full phone and staff flow. | Connect the map/geofence, cart, help, order status and reconnect screens. Test screen readers, large text and contrast on real devices; measure time to order at the pilot cafe. |

## Backend follow-up

| Task | Current gap |
| --- | --- |
| Make session expiry explicit. | Done: reads report expiry; periodic cleanup persists it, releases the kiosk and publishes an event. |
| Add response schemas. | Most responses are generic dictionaries. Define the actual fields so `/docs` gives clients a useful response contract. |
| Improve recovery after disconnects. | Events have no replay; clients must refetch state. Stock changes also need a live event if menus should update immediately. |
| Add database migrations. | Startup creates missing tables only. Schema changes need a migration path before keeping pilot data. |
| Add rate limits and device-token revocation. | Registration and pairing have no throttling; phone tokens have no expiry or revoke endpoint. |
| Add a database readiness check. | `/health` only confirms the app responds. |

## Later, if needed

- Store/menu editing: currently done through the seed script, apart from item availability. Add staff editing and a way to keep accessibility details current.
- Payments: `paymentMethod` only records a choice. Agree on the payment flow before adding payment processing.
- Scaling: add a shared event broker before running multiple workers; add pagination and database-side nearby search as store/order counts grow.
- Voice ordering and indoor guidance: still product work to explore and test in a noisy cafe.
