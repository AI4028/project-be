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
| Add response schemas. | Done: typed responses document store, session, order, cart and event fields in `/docs`. |
| Improve recovery after disconnects. | Done: authenticated reconnect snapshots and live stock events. Clients recover current state; historical events are not replayed. |
| Add database migrations. | Done: versioned migrations and checked adoption of the existing schema. [Usage](migrations.md) |
| Add rate limits and device-token revocation. | Done: registration/pairing limits and self-service phone-token revocation. Limits are process-local; tokens remain valid until revoked. |
| Add a database readiness check. | Done: `/ready` checks database/schema access and returns 503 on failure; `/health` remains liveness. |

## Later, if needed

- Store/menu editing: currently done through the seed script, apart from item availability. Add staff editing and a way to keep accessibility details current.
- Payments: `paymentMethod` only records a choice. Agree on the payment flow before adding payment processing.
- Scaling: add a shared event broker before running multiple workers; add pagination and database-side nearby search as store/order counts grow.
- Voice ordering and indoor guidance: still product work to explore and test in a noisy cafe.
