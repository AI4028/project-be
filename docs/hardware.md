# Hardware

A prototype Bluetooth beacon for the kiosk.

| Path | What |
| --- | --- |
| `hardware/galjido_kiosk_beacon/` | Arduino sketch. Sends a beacon packet every 0.5 s |
| `hardware/change_bt_name/` | Renames the Bluetooth module with AT commands |
| `hardware/bt_bridge.py` | Reads packets from a COM port and posts them to `POST /proximity` |

## Wiring

Arduino Uno or Nano with a ZS-040 (HC-05 family) module.

| ZS-040 | Arduino |
| --- | --- |
| VCC | 5V |
| GND | GND |
| TXD | D2 |
| RXD | D3 |

## Bridge

Pair the module with Windows and note its COM port. Start the API with
`DEMO_MODE=1`, then:

```powershell
pip install -r hardware/requirements.txt
python hardware/bt_bridge.py COM4
```

Set `BACKEND_URL` if the API isn't at `http://127.0.0.1:8000`. Readings stream
to `ws://HOST/ws/proximity`.

## Known gaps

- The sketch sends `STORE`, `KIOSK`, `TX` and `SEQ`, but the bridge expects
  `DIST`. Until one side changes, the bridge posts nothing.
- The beacon doesn't broadcast a pairing token, so real pairing
  ([format](api.md#bluetooth-advertisement)) still needs the kiosk app. Demo
  mode covers it for now.
