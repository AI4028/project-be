"""bt_bridge.py - 아두이노 ZS-040 블루투스 시리얼 브리지

윈도우에서 HC-05와 페어링된 가상 COM 포트(예: COM3, COM4 등)로부터
아두이노 거리 패킷(DIST:xx)을 수신하여 백엔드 POST /proximity 로 전달합니다.
백엔드는 이를 /ws/proximity 웹소켓으로 프론트엔드에 실시간 전달합니다.

백엔드는 DEMO_MODE=1 로 실행되어 있어야 합니다 (app/routers/demo.py 참고).

사용법:
  pip install -r hardware/requirements.txt
  python hardware/bt_bridge.py COM4

백엔드 주소 변경: 환경 변수 BACKEND_URL (기본값 http://127.0.0.1:8000)
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
    print("pyserial 라이브러리가 필요합니다: pip install -r hardware/requirements.txt")
    sys.exit(1)

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
KIOSK_ID = "GK01"
TX_POWER = -59  # 1m 기준 신호 세기 (dBm), 아두이노 스케치와 동일


def post_proximity(distance, store_name):
    rssi = int(round(TX_POWER - 22 * math.log10(max(0.1, distance))))
    body = json.dumps({"distance": distance, "storeName": store_name, "kioskId": KIOSK_ID, "rssi": rssi}).encode("utf-8")
    req = urllib.request.Request(f"{BACKEND_URL}/proximity", data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=1)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            print("   ⚠️ 백엔드가 DEMO_MODE=1 로 실행되지 않았습니다 (POST /proximity 404).")
    except OSError:
        print(f"   ⚠️ 백엔드({BACKEND_URL})에 연결할 수 없습니다.")


def main():
    if len(sys.argv) < 2:
        print("사용법: python hardware/bt_bridge.py <COM포트번호>")
        print("예시: python hardware/bt_bridge.py COM4")
        return

    port = sys.argv[1].upper()
    baudrate = 9600

    print(f"[{port}] 아두이노 ZS-040 블루투스 시리얼 연결 시도 중 ({baudrate} baud)...")

    try:
        ser = serial.Serial(port, baudrate, timeout=2)
        time.sleep(1)
        print(f"✅ {port} 포트에 성공적으로 연결되었습니다!")
        print("아두이노로부터 거리 데이터 수신 대기 중 (종료: Ctrl+C)...\n")

        while True:
            if ser.in_waiting > 0:
                line = ser.readline().decode("utf-8", errors="replace").strip()
                if line:
                    print(f"📡 [수신] {line}")
                    if "DIST:" in line:
                        try:
                            distance = float(line.split("DIST:")[1].split(",")[0].strip())
                        except ValueError:
                            continue
                        store_name = "GIST Cafe점"
                        if "STORE:" in line:
                            store_name = line.split("STORE:")[1].split(",")[0].strip()
                        print(f"   👉 감지된 거리: {distance}m (매장: {store_name})")
                        post_proximity(distance, store_name)
                        if distance <= 100:
                            print("   🔔 [조건 달성] 100m 이내 매장 감지 -> 앱에서 '매장을 연결할까요?' 음성 발화!")
            time.sleep(0.05)

    except serial.SerialException as e:
        print(f"❌ 시리얼 포트 열기 실패: {e}")
        print("팁: 윈도우 블루투스 설정에서 HC-05가 정상 페어링되어 있는지, 다른 프로그램이 해당 COM 포트를 점유하고 있지 않은지 확인하세요.")
    except KeyboardInterrupt:
        print("\n모니터링을 종료합니다.")


if __name__ == "__main__":
    main()
