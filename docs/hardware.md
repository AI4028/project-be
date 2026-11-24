# Hardware

## BLE pairing bridge

`hardware/ble_kiosk_bridge.py` fetches `POST /kiosk/heartbeat` with the kiosk's
existing API key. Install the serial dependency, set `KIOSK_API_KEY` in the
helper process's environment, then run the helper with the ESP32's USB port.
Use a synchronized clock on the kiosk computer.

```sh
python -m pip install -r hardware/requirements.txt
python hardware/ble_kiosk_bridge.py /dev/cu.usbserial-0001 --backend-url http://127.0.0.1:8000
```

The USB protocol is 115200 baud and one ASCII line per successful refresh.
For example, `ADV LKGK017H3KQ9ZC 59000\n` supplies the 14-character
advertisement payload and its remaining lifetime in milliseconds. The bridge
subtracts one second from the server expiry before sending the lifetime.
The [ESP32 sketch](../hardware/galjido_ble_beacon/) starts idle and publishes the
payload as the complete local name in a legacy, non-connectable BLE advertisement.
It replaces the name when the token rotates, updates the deadline when the same
token arrives again, and stops at expiry. The firmware uses the board's monotonic
clock and accepts ASCII `ADV <payload> <lifetimeMs>` lines terminated by LF, with a
lifetime from 1 through 60000 ms. It discards malformed lines without refreshing
the deadline and resumes parsing after the next line break.

The sketch builds with Arduino ESP32 core **3.3.x** for two radio stacks:

- **XIAO ESP32-C3 / S3 / C6** use NimBLE (Bluedroid is disabled there). The
  sketch calls the NimBLE GAP API directly (`ble_gap_adv_set_data`,
  `ble_gap_adv_start`); the Arduino `BLEAdvertising` wrapper crashed on the
  XIAO ESP32-C3 (null pointer on the first `ADV` line). Tested on a XIAO ESP32-C3:
  the phone sees `LKGK01…` with the kiosk's current code.
- **ESP32 Dev Module** uses Bluedroid through `BLEAdvertising`.

With the core installed, build it without a board attached.

```sh
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C3 hardware/galjido_ble_beacon
arduino-cli compile --fqbn esp32:esp32:esp32 hardware/galjido_ble_beacon
```

Attach the XIAO's external antenna; without it the signal is weak and jumpy.

To test the same frame parser, advertisement bytes, and expiry logic on a
computer with a C++11 compiler, run the fake-radio test from the repository root.

```sh
c++ -std=c++11 -Wall -Wextra -Werror -pedantic \
  -I hardware/galjido_ble_beacon hardware/galjido_ble_beacon/beacon.cpp \
  hardware/tests/ble_beacon_test.cpp -o /tmp/galjido-ble-beacon-test
/tmp/galjido-ble-beacon-test
```

## Position boards (three-board kiosk finding)

The app's kiosk finder (`project-fe`, `src/lib/ble-position.ts`) can use two extra
boards at measured spots next to the kiosk board, to work out the phone's position
and point an arrow to the kiosk. Each runs
[`galjido_ble_anchor`](../hardware/galjido_ble_anchor/) and broadcasts a fixed
local name, `LA` + kiosk id + letter (`LAGK01B`, `LAGK01C`), in a legacy,
non-connectable advertisement every 100–150 ms. It needs only USB power: no
bridge, laptop or network. Set `KIOSK_ID` and `ANCHOR_LETTER` (`'B'` or `'C'`) at
the top of the sketch before flashing each board. The Serial Monitor (115200)
prints `GALJIDO ANCHOR READY LAGK01B`, then `ANCHOR ON LAGK01B`.

```sh
arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32C3 hardware/galjido_ble_anchor
```

Placement and setup:

1. Place the kiosk board and boards B and C in a triangle, 2–3 m apart, at chest
   height, with the customers' path (door to kiosk) inside or near the triangle.
2. Measure in metres with the kiosk board as (0, 0) and "forward" toward board B.
   Example: B (0, 4) and C (3, 2), where C is 3 m to the right and 2 m forward.
3. On the phone's kiosk finder, open **보드 3개 설정**:
   - enter the spots;
   - at the kiosk, face board B and save the forward direction;
   - calibrate each board from 1 m.

In simulation, the position inside the triangle is within about 1 m and the arrow
within about 5–15°. Outside the triangle, the app reports that the position is
unsure and falls back to one-board guidance.

## Arduino Bluetooth Classic prototype

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
- The Bluetooth Classic prototype only sends distance-demo packets. The ESP32
  sketch above implements the [pairing payload](api.md#bluetooth-advertisement).
