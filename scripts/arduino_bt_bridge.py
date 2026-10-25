"""arduino_bt_bridge.py - 아두이노 ZS-040 블루투스 시리얼 테스트 브리지

윈도우에서 HC-05와 페어링된 가상 COM 포트(예: COM3, COM4 등)로부터
아두이노 거리 패킷(DIST:xx)을 수신하고 정상 동작하는지 실시간 모니터링합니다.

사용법:
  python scripts/arduino_bt_bridge.py COM4
"""

import sys
import time

try:
    import serial
except ImportError:
    print("pyserial 라이브러리가 필요합니다: pip install pyserial")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("사용법: python scripts/arduino_bt_bridge.py <COM포트번호>")
        print("예시: python scripts/arduino_bt_bridge.py COM4")
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
                        dist_val = line.split("DIST:")[1].split(",")[0].strip()
                        store_name = "GIST Cafe점"
                        if "STORE:" in line:
                            store_name = line.split("STORE:")[1].split(",")[0].strip()
                        print(f"   👉 감지된 거리: {dist_val}m (매장: {store_name})")
                        # 백엔드 서버로 실시간 거리 전송 -> 프론트엔드 웹소켓으로 즉시 전달됨!
                        try:
                            import json
                            import urllib.request
                            import math
                            d = max(0.1, float(dist_val))
                            calc_rssi = int(round(-59 - 22 * math.log10(d)))
                            req_data = json.dumps({"distance": float(dist_val), "storeName": store_name, "kioskId": "GK01", "rssi": calc_rssi}).encode('utf-8')
                            req = urllib.request.Request("http://127.0.0.1:8000/proximity", data=req_data, headers={'Content-Type': 'application/json'})
                            urllib.request.urlopen(req, timeout=1)
                        except Exception as post_err:
                            pass
                        if float(dist_val) <= 100:
                            print("   🔔 [조건 달성] 100m 이내 매장 감지 -> 앱에서 '매장을 연결할까요?' 음성 발화!")
            time.sleep(0.05)

    except serial.SerialException as e:
        print(f"❌ 시리얼 포트 열기 실패: {e}")
        print("팁: 윈도우 블루투스 설정에서 HC-05가 정상 페어링되어 있는지, 다른 프로그램이 해당 COM 포트를 점유하고 있지 않은지 확인하세요.")
    except KeyboardInterrupt:
        print("\n모니터링을 종료합니다.")


if __name__ == "__main__":
    main()
