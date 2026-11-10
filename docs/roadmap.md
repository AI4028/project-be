# Roadmap

## Features

| Stage | Feature | Priority | Status |
| --- | --- | --- | --- |
| Access | Store accessibility info | Must | API done, map UI next |
| Access | Geofence store detection | Must | API done, client next |
| Ordering method | Ordering methods per store | Must | API done |
| Ordering | Menu, prices and options on the phone | Must | Done |
| Ordering | Phone-to-kiosk pairing, live orders | Must | Done, real Bluetooth pairing pending |
| Ordering | Voice ordering | Should | Exploring |
| Ordering method | In-store guidance to the kiosk | Should | Exploring (beacon prototype) |

Must ships in the first release. Should comes after.

## Next

1. Map UI per disability type, with geofencing on the phone.
2. Real data for the pilot cafe (replace the placeholders in `seed/gist-cafe.json`).
3. Real Bluetooth pairing: the kiosk broadcasts its token.
4. Accessibility pass on the UI: screen reader, magnification, contrast.
5. Pilot at a GIST campus cafe, then stores in Seongsu, Seoul. Measure time to order.

## Risks

- Bluetooth support varies by phone and browser.
- Indoor proximity is noisy.
- Store noise hurts voice input.
- Accessibility data goes stale without a way to update it.
- One phone per kiosk. A second phone gets `kiosk-busy`.
