# 아두이노

#include <Wire.h>

# const int pressurePin = A0; // 압력 센서 연결 핀
# const int threshold = 500;   // 임계값

# void setup() {
#   Serial.begin(9600); // 시리얼 통신 시작
# }

# void loop() {
#   int pressureValue = analogRead(pressurePin); // 압력 센서 값 읽기

#   if (pressureValue > threshold) {
#     Serial.println("Alert!"); // 임계값 초과 시 경고 메시지 전송
#     delay(1000); // 1초 대기
#   }
# }
