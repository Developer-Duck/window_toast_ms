# 라즈베리파이

# import serial
# import os

# # 아두이노와의 시리얼 연결
# arduino = serial.Serial('/dev/ttyUSB0', 9600)  # 아두이노가 연결된 포트로 변경하세요

# while True:
#     if arduino.in_waiting > 0:  # 수신된 데이터가 있는지 확인
#         message = arduino.readline().decode('utf-8').strip()  # 메시지 읽기
#         if message == "Alert!":  # "Alert!" 메시지가 수신되면
#             # EXE 파일 실행
#             os.system("C:\\path\\to\\dist\\자세교정 ai.exe")  # EXE 파일 경로를 올바르게 변경하세요