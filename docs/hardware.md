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

The sketch targets the **ESP32 Dev Module** with the Bluedroid stack in Arduino
ESP32 core **3.3.7**. With that core installed, build it without a board attached.

```sh
arduino-cli compile --fqbn esp32:esp32:esp32 hardware/galjido_ble_beacon
```

To test the same frame parser, advertisement bytes, and expiry logic on a
computer with a C++11 compiler, run the fake-radio test from the repository root.

```sh
c++ -std=c++11 -Wall -Wextra -Werror -pedantic \
  -I hardware/galjido_ble_beacon hardware/galjido_ble_beacon/beacon.cpp \
  hardware/tests/ble_beacon_test.cpp -o /tmp/galjido-ble-beacon-test
/tmp/galjido-ble-beacon-test
```

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
