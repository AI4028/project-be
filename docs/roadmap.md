# What we should work on

The backend has store lookup, nearby search, anonymous phone auth, pairing,
cart pricing, orders, staff help, stock toggles and live updates. Tests cover
the core flow; CI is configured for SQLite and Postgres.

Backend follow-up work below is implemented. Frontend checkout and reconnect
integration is on `feature/ordering-readiness` in the adjacent
`project-fe-readiness` checkout (branched from frontend `develop`).

## Before the pilot

| Priority | Task | Why / done when |
| --- | --- | --- |
| 1 | Replace the demo cafe data. | Prices, location and accessibility values are placeholders. Visit the store and update [gist-cafe.json](../seed/gist-cafe.json), including indoor directions. |
| 2 | Verify the full phone and staff flow. | Pair using the kiosk’s BLE broadcast, QR code, or manual code, request help, submit a pay-at-café order, and check staff acknowledgement and order status. Test screen readers, large text and contrast on real devices. |

## Backend work completed

| Task | Result |
| --- | --- |
| Make session expiry explicit. | Done: reads report expiry; periodic cleanup persists it, releases the kiosk and publishes an event. |
| Add response schemas. | Done: typed responses document store, session, order, cart and event fields in `/docs`. |
| Improve recovery after disconnects. | Done: authenticated reconnect snapshots and live stock events. Clients recover current state; historical events are not replayed. |
| Add database migrations. | Done: versioned migrations and checked adoption of the existing schema. [Usage](migrations.md) |
| Add rate limits and device-token revocation. | Done: registration/pairing limits and self-service phone-token revocation. Limits are process-local; tokens remain valid until revoked. |
| Add a database readiness check. | Done: `/ready` checks database/schema access and returns 503 on failure; `/health` remains liveness. |

## Later, if needed

- Store/menu editing: currently done through the seed script, apart from item availability. Add staff editing and a way to keep accessibility details current.
- Live checkout records payment at the café. Card and wallet simulation is available on demo backends. Online payment processing would require a separate integration.
- Live beacon guidance is prototype work. Reconcile the beacon packet and bridge formats, implement rotating-token broadcast, and test on site before offering live navigation. [Hardware gaps](hardware.md#known-gaps)
- Scaling: add a shared event broker before running multiple workers; add pagination and database-side nearby search as store/order counts grow.
- Voice ordering and indoor guidance: still product work to explore and test in a noisy cafe.

## Checkout integration

The frontend review identified two additional blockers. Backend support is now
in place: persistent idempotent order retries and server-validated price quotes.
Frontend adoption, typechecking, unit tests and web export pass.

## Still needs real-world verification

Hardware integration, verified cafe details, and real-device accessibility/permission
checks remain. Automated checks do not establish these. Postgres could not be run
locally because Docker Desktop's engine is stopped; CI still runs the API suite on it.
Push notifications remain future work. Staff can acknowledge help from an active
session or an open order through the kiosk. [API contract](api.md#staff-help-delivery)
