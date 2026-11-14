# Docs

Galjido helps people check store accessibility and order from their own phone.
The backend handles store data, kiosk pairing, carts, staff help and order updates.

- **[API reference](api.md):** every endpoint, its Python function, inputs, results and live events.
- **[What to work on](roadmap.md):** current gaps and a short priority list.
- [Overview](overview.md): what Galjido is, who it's for, how the parts fit
- [Map](map.md): disability-specific maps and the store data behind them
- [Hardware](hardware.md): kiosk Bluetooth beacon and serial bridge

## Where the code lives

| File | Job |
| --- | --- |
| [routers/](../app/routers/) | HTTP and WebSocket endpoints. |
| [service.py](../app/service.py) | Pairing, carts, orders, help and database transactions. |
| [logic.py](../app/logic.py) | Menu validation, pricing, token checks, distances and order status rules. |
| [auth.py](../app/auth.py) | Issues phone tokens and checks phone/kiosk credentials. |
| [schemas.py](../app/schemas.py), [models.py](../app/models.py) | Request bodies and database tables. |
| [realtime.py](../app/realtime.py) | Sends events to connected kiosks and phones. |
| [scripts/](../scripts/) | Loads store data and issues kiosk keys. |
