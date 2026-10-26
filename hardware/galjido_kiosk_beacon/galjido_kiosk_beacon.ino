/*
 * ==============================================================================
 * galjido_kiosk_beacon.ino - 지스트 카페(GIST Cafe) 키오스크 블루투스 비콘
 * ==============================================================================
 * 
 * [시스템 설계 원칙]
 * 1. 100% 자동 거리 측정: 사람이나 사용자가 키보드로 숫자를 입력할 필요가 전혀 없습니다.
 * 2. 물리 센서(초음파/레이저) 불필요: 벽이나 장애물이 있어도 전파는 통과하므로
 *    블루투스 모듈 1개의 전파 세기(RSSI, dBm) 감쇄 모델로 거리를 완전 자동으로 측정합니다.
 * 3. 하드웨어 구성: 아두이노(Uno/Nano) + ZS-040 블루투스 모듈 1개 단독
 * 
 * [회로 연결 (블루투스 모듈 <-> 아두이노)]
 * -------------------------------------------------------------
 *  ZS-040 핀    <--->   아두이노 핀        설명
 * -------------------------------------------------------------
 *  VCC          <--->   5V (또는 3.3V)    전원 공급
 *  GND          <--->   GND              접지
 *  TXD          <--->   D2 (RX)          아두이노 수신
 *  RXD          <--->   D3 (TX)          아두이노 송신
 * -------------------------------------------------------------
 * 
 * [작동 방식]
 * - 아두이노는 키오스크 위치에서 고정된 송신 출력(TxPower: -59dBm)으로 
 *   블루투스 비콘 전파를 0.5초마다 사방으로 방출합니다.
 * - 사용자가 스마트폰을 들고 걸어오면, 스마트폰의 블루투스 수신기가 전파 세기(RSSI)를
 *   실시간으로 측정하여 거리(미터)를 계산합니다:
 *      Distance = 10 ^ ((TxPower - RSSI) / (10 * n))
 * - 가까워질수록 RSSI 세기가 증가(-85dBm -> -65dBm -> -45dBm)하여 거리가 자동으로 줄어듭니다!
 */

#include <SoftwareSerial.h>

// D2: RX (블루투스 TXD 연결), D3: TX (블루투스 RXD 연결)
SoftwareSerial BTSerial(2, 3);

// 매장 및 비콘 식별 정보
const char* STORE_NAME = "GIST Cafe점";
const char* KIOSK_ID   = "GK01";
const int   TX_POWER   = -59; // 1m 기준 기준 신호 세기 (dBm)

unsigned long lastBeaconTime = 0;
const unsigned long beaconInterval = 500; // 0.5초마다 비콘 신호 방출
unsigned long packetCount = 0;

void setup() {
  Serial.begin(9600);    // PC 시리얼 모니터 (모니터링 전용)
  BTSerial.begin(9600);  // ZS-040 블루투스

  Serial.println(F("=========================================================="));
  Serial.println(F(" ☕ GIST Cafe 키오스크 블루투스 비콘 가동 시작!"));
  Serial.println(F("----------------------------------------------------------"));
  Serial.println(F(" [동작 모드] 블루투스 전파 세기(RSSI) 100% 자동 거리 측정"));
  Serial.println(F(" [하드웨어] 아두이노 + ZS-040 블루투스 모듈 1개 단독"));
  Serial.println(F(" - 수동 숫자 입력 없음!"));
  Serial.println(F(" - 벽/장애물에 막히는 초음파/레이저 센서 없음!"));
  Serial.println(F(" - 스마트폰이 전파 세기(RSSI dBm)를 측정해 거리를 자동 계산합니다."));
  Serial.println(F("=========================================================="));
}

void loop() {
  unsigned long currentMillis = millis();

  // 1. 스마트폰 또는 모듈로부터 들어온 데이터가 있다면 시리얼 모니터에 출력
  if (BTSerial.available()) {
    char c = BTSerial.read();
    Serial.write(c);
  }

  // 2. 0.5초마다 키오스크 고유 비콘 신호 자동 송신
  if (currentMillis - lastBeaconTime >= beaconInterval) {
    lastBeaconTime = currentMillis;
    packetCount++;

    // 웹 앱 및 스마트폰 수신기에서 인식하는 표준 비콘 패킷 방출
    // 예: STORE:GIST Cafe점,KIOSK:GK01,TX:-59,SEQ:123
    BTSerial.print(F("STORE:"));
    BTSerial.print(STORE_NAME);
    BTSerial.print(F(",KIOSK:"));
    BTSerial.print(KIOSK_ID);
    BTSerial.print(F(",TX:"));
    BTSerial.print(TX_POWER);
    BTSerial.print(F(",SEQ:"));
    BTSerial.println(packetCount);

    // PC 시리얼 모니터 상태 표시 (진행 상태 확인용)
    if (packetCount % 4 == 0) { // 2초마다 1줄씩 로그
      Serial.print(F("[비콘 전파 송신 중] 패킷 #"));
      Serial.print(packetCount);
      Serial.print(F(" | TxPower: "));
      Serial.print(TX_POWER);
      Serial.println(F("dBm (스마트폰이 RSSI로 실시간 거리 자동 측정)"));
    }
  }
}
