/*
 * galjido_kiosk_beacon.ino - GIST Cafe 키오스크 블루투스 비콘
 *
 * 하드웨어: 아두이노(Uno/Nano) + ZS-040 블루투스 모듈
 *
 *   ZS-040   아두이노
 *   VCC      5V (또는 3.3V)
 *   GND      GND
 *   TXD      D2 (RX)
 *   RXD      D3 (TX)
 *
 * 0.5초마다 고정 출력(TX_POWER)으로 비콘 패킷을 보냅니다. 스마트폰은 수신 세기(RSSI)로
 * 거리를 계산합니다: Distance = 10 ^ ((TxPower - RSSI) / (10 * n))
 */

#include <SoftwareSerial.h>

SoftwareSerial BTSerial(2, 3);  // RX, TX

const char* STORE_NAME = "GIST Cafe점";
const char* KIOSK_ID   = "GK01";
const int   TX_POWER   = -59;  // 1m 기준 신호 세기 (dBm)

const unsigned long BEACON_INTERVAL_MS = 500;
unsigned long lastBeaconTime = 0;
unsigned long packetCount = 0;

void setup() {
  Serial.begin(9600);    // PC 시리얼 모니터
  BTSerial.begin(9600);  // ZS-040
  Serial.println(F("GIST Cafe 키오스크 비콘 시작"));
}

void loop() {
  unsigned long now = millis();

  // 모듈로 들어온 데이터를 시리얼 모니터에 출력
  if (BTSerial.available()) {
    Serial.write(BTSerial.read());
  }

  if (now - lastBeaconTime >= BEACON_INTERVAL_MS) {
    lastBeaconTime = now;
    packetCount++;

    // 예: STORE:GIST Cafe점,KIOSK:GK01,TX:-59,SEQ:123
    BTSerial.print(F("STORE:"));
    BTSerial.print(STORE_NAME);
    BTSerial.print(F(",KIOSK:"));
    BTSerial.print(KIOSK_ID);
    BTSerial.print(F(",TX:"));
    BTSerial.print(TX_POWER);
    BTSerial.print(F(",SEQ:"));
    BTSerial.println(packetCount);

    if (packetCount % 4 == 0) {  // 2초마다 로그
      Serial.print(F("[비콘] 패킷 #"));
      Serial.print(packetCount);
      Serial.print(F(" | TxPower: "));
      Serial.print(TX_POWER);
      Serial.println(F("dBm"));
    }
  }
}
