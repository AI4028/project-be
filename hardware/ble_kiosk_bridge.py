"""Forward real kiosk heartbeat tokens to an ESP32 over USB serial."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

BAUD_RATE = 115200
MAX_TOKEN_LIFETIME_MS = 60_000
EXPIRY_MARGIN_MS = 1_000
RETRY_SECONDS = 2
ADVERTISEMENT = re.compile(r"LK[A-Z0-9]{4}[0-9A-HJKMNP-TV-Z]{8}")


def fetch_heartbeat(backend_url: str, kiosk_key: str) -> dict:
    request = Request(f"{backend_url.rstrip('/')}/kiosk/heartbeat", method="POST")
    request.add_unredirected_header("Authorization", f"Bearer {kiosk_key}")
    with urlopen(request, timeout=5) as response:
        return json.load(response)


def heartbeat_frame(heartbeat: dict, now_ms: int) -> tuple[bytes, float]:
    """Return the USB frame and the delay before asking for another heartbeat."""
    payload = f"LK{heartbeat['kioskId']}{heartbeat['token']}"
    expires_at_ms = heartbeat["expiresAtMs"]
    refresh_in_ms = heartbeat["refreshInMs"]
    if (
        not ADVERTISEMENT.fullmatch(payload)
        or not isinstance(heartbeat["kioskId"], str)
        or len(heartbeat["kioskId"]) != 4
        or not isinstance(heartbeat["token"], str)
        or type(expires_at_ms) is not int
        or type(refresh_in_ms) is not int
        or refresh_in_ms <= 0
    ):
        raise ValueError("Invalid kiosk heartbeat")
    lifetime_ms = expires_at_ms - now_ms - EXPIRY_MARGIN_MS
    if lifetime_ms <= 0 or lifetime_ms > MAX_TOKEN_LIFETIME_MS:
        raise ValueError("Heartbeat expiry is outside the usable window")
    return f"ADV {payload} {lifetime_ms}\n".encode("ascii"), min(refresh_in_ms, lifetime_ms) / 1000


def update_beacon(port, backend_url: str, kiosk_key: str) -> float:
    heartbeat = fetch_heartbeat(backend_url, kiosk_key)
    frame, delay = heartbeat_frame(heartbeat, time.time_ns() // 1_000_000)
    if port.write(frame) != len(frame):
        raise OSError("Incomplete serial write")
    return delay


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="USB serial port, for example COM4 or /dev/cu.usbserial-0001")
    parser.add_argument("--backend-url", default=os.getenv("BACKEND_URL", "http://127.0.0.1:8000"))
    args = parser.parse_args()
    kiosk_key = os.getenv("KIOSK_API_KEY")
    if not kiosk_key:
        parser.error("Set KIOSK_API_KEY to the staff kiosk's key.")
    try:
        import serial
    except ImportError:
        parser.error("Install pyserial with pip install -r hardware/requirements.txt.")

    while True:
        try:
            with serial.Serial(args.port, BAUD_RATE, write_timeout=1) as port:
                time.sleep(RETRY_SECONDS)  # Opening USB serial can reset the board.
                print("USB connected. Forwarding kiosk heartbeats.", flush=True)
                while True:
                    try:
                        delay = update_beacon(port, args.backend_url, kiosk_key)
                    except serial.SerialException:
                        raise
                    except HTTPError as error:
                        print(f"Kiosk heartbeat returned HTTP {error.code}. Retrying.", flush=True)
                        delay = RETRY_SECONDS
                    except (OSError, KeyError, TypeError, ValueError):
                        print("Could not forward the kiosk heartbeat. Retrying.", flush=True)
                        delay = RETRY_SECONDS
                    time.sleep(delay)
        except serial.SerialException:
            print("USB serial is unavailable. Retrying.", flush=True)
            time.sleep(RETRY_SECONDS)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
