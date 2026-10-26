/*
 * ==============================================================================
 * change_bt_name.ino - 아두이노 블루투스(ZS-040 / HC-05 / HC-06 / HM-10) 이름 변경 도구
 * ==============================================================================
 * 
 * [사용 방법]
 * 1. 이 코드를 아두이노에 업로드합니다.
 * 2. 아두이노 IDE의 [시리얼 모니터]를 엽니다.
 * 3. 오른쪽 아래 전송 설정을 [Both NL & CR] (또는 보드에 맞게) 및 [9600 baud]로 맞춥니다.
 * 4. 시리얼 모니터에 AT 명령어를 입력하거나, setup()에서 자동 변경됩니다.
 */

#include <SoftwareSerial.h>

// D2: RX (블루투스 TXD 연결), D3: TX (블루투스 RXD 연결)
SoftwareSerial BTSerial(2, 3);

// ★ 여기에 설정하고 싶은 블루투스 이름을 적어주세요 (영문/숫자 권장)
const char* NEW_BT_NAME = "Test01_GIST_Cafe"; 

void setup() {
  Serial.begin(9600);
  
  // HC-05의 AT 모드는 기본 38400, HC-06 / HM-10은 기본 9600입니다.
  BTSerial.begin(9600); 

  Serial.println(F("=================================================="));
  Serial.println(F(" 🔧 아두이노 블루투스 기기 이름 변경 도구"));
  Serial.println(F("=================================================="));
  Serial.println(F("시리얼 모니터에서 직접 AT 명령어를 입력할 수도 있습니다."));
  Serial.println(F("예) AT -> OK 확인"));
  Serial.println(F("--------------------------------------------------"));

  delay(500);

  // 1. 통신 확인 (AT)
  Serial.println(F("1. 연결 상태 확인 중 (AT)..."));
  BTSerial.print("AT\r\n");
  delay(300);

  // 2. 이름 변경 시도 (HM-10 / AT-09 BLE 방식)
  Serial.print(F("2. 이름 변경 전송 시도 -> "));
  Serial.println(NEW_BT_NAME);
  
  // HM-10 / AT-09 표준
  BTSerial.print("AT+NAME");
  BTSerial.print(NEW_BT_NAME);
  BTSerial.print("\r\n");
  delay(300);

  // HC-05 방식 (AT+NAME=이름)
  BTSerial.print("AT+NAME=");
  BTSerial.print(NEW_BT_NAME);
  BTSerial.print("\r\n");
  delay(300);

  // HC-06 방식 (줄바꿈 없음)
  BTSerial.print("AT+NAME");
  BTSerial.print(NEW_BT_NAME);
  delay(300);

  Serial.println(F("--------------------------------------------------"));
  Serial.println(F("명령어 전송 완료! 아래에 모듈의 응답(OK)이 출력됩니다."));
}

void loop() {
  // 블루투스 모듈 응답 -> PC 시리얼 모니터로 출력
  if (BTSerial.available()) {
    Serial.write(BTSerial.read());
  }

  // PC 시리얼 모니터 입력 -> 블루투스 모듈로 전달
  if (Serial.available()) {
    BTSerial.write(Serial.read());
  }
}
