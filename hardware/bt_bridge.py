"""아두이노 ZS-040 블루투스 시리얼 브리지.

블루투스 가상 COM 포트에서 거리 패킷(DIST:xx)을 읽어 백엔드 POST /proximity 로 보냅니다.
백엔드는 /ws/proximity 로 프론트엔드에 전달합니다. 백엔드는 DEMO_MODE=1 로 실행해야 합니다.

    pip install -r hardware/requirements.txt
    python hardware/bt_bridge.py COM4

BACKEND_URL 환경 변수로 백엔드 주소 변경 (기본값 http://127.0.0.1:8000).
"""

import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

try:
    import serial
except ImportError:
    sys.exit("pyserial 이 필요합니다: pip install -r hardware/requirements.txt")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
BAUDRATE = 9600
KIOSK_ID = "GK01"
DEFAULT_STORE = "GIST Cafe점"
TX_POWER = -59  # 1m 기준 신호 세기 (dBm), 아두이노 스케치와 동일
NEARBY_M = 100


def post_proximity(distance, store_name):
    rssi = int(round(TX_POWER - 22 * math.log10(max(0.1, distance))))
    body = json.dumps({"distance": distance, "storeName": store_name, "kioskId": KIOSK_ID, "rssi": rssi}).encode("utf-8")
    req = urllib.request.Request(f"{BACKEND_URL}/proximity", data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=1)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            print("   백엔드가 DEMO_MODE=1 로 실행되지 않았습니다 (POST /proximity 404).")
    except OSError:
        print(f"   백엔드({BACKEND_URL})에 연결할 수 없습니다.")


def parse(line):
    """'STORE:GIST Cafe점,DIST:2.5' -> (2.5, 'GIST Cafe점'), or None."""
    if "DIST:" not in line:
        return None
    try:
        distance = float(line.split("DIST:")[1].split(",")[0].strip())
    except ValueError:
        return None
    store = line.split("STORE:")[1].split(",")[0].strip() if "STORE:" in line else DEFAULT_STORE
    return distance, store


def main():
    if len(sys.argv) < 2:
        print("사용법: python hardware/bt_bridge.py <COM포트>  (예: COM4)")
        return

    port = sys.argv[1].upper()
    print(f"[{port}] 연결 중 ({BAUDRATE} baud)...")

    try:
        ser = serial.Serial(port, BAUDRATE, timeout=2)
        time.sleep(1)
        print(f"{port} 연결됨. 거리 데이터 대기 중 (종료: Ctrl+C)\n")

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    print(f"[수신] {line}")
                    reading = parse(line)
                    if reading:
                        distance, store = reading
                        print(f"   거리: {distance}m (매장: {store})")
                        post_proximity(distance, store)
                        if distance <= NEARBY_M:
                            print(f"   {NEARBY_M}m 이내 매장 감지")
            time.sleep(0.05)

    except serial.SerialException as e:
        print(f"시리얼 포트 열기 실패: {e}")
        print("윈도우 블루투스 설정에서 모듈이 페어링되어 있는지, 다른 프로그램이 포트를 쓰고 있지 않은지 확인하세요.")
    except KeyboardInterrupt:
        print("\n종료합니다.")


if __name__ == "__main__":
    main()
