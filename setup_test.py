

import sys
import subprocess
import paramiko
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout

class MyApp(QWidget):
    def __init__(self):
        super().__init__()
        
        # 윈도우 창 타이틀과 크기 설정
        self.setWindowTitle('PyQt5 Raspberry Pi 연결 예제')
        self.setGeometry(300, 300, 400, 200)

        # 레이아웃 설정
        layout = QVBoxLayout()

        # 라벨: SSH 연결 상태
        self.label_status = QLabel('Raspberry Pi와 연결 상태: 확인 중...', self)
        layout.addWidget(self.label_status)

        # 연결 확인 버튼 추가
        self.button_check_connection = QPushButton('Raspberry Pi 연결 확인', self)
        self.button_check_connection.clicked.connect(self.check_connection)
        layout.addWidget(self.button_check_connection)

        # 실행 버튼 추가
        self.button_execute = QPushButton('EXE 파일 실행', self)
        self.button_execute.clicked.connect(self.execute_file)
        layout.addWidget(self.button_execute)

        # 레이아웃 설정
        self.setLayout(layout)

    # SSH 연결 상태 확인 함수
    def check_connection(self):
        try:
            # Raspberry Pi에 SSH 연결
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect('raspberrypi_IP', username='pi', password='비밀번호')  # Raspberry Pi 정보 입력
            self.label_status.setText('Raspberry Pi와 연결됨!')
            ssh.close()
        except Exception as e:
            self.label_status.setText('Raspberry Pi 연결 실패: ' + str(e))

    # exe 파일 실행 함수
    def execute_file(self):
        try:
            # 특정 EXE 파일 실행
            subprocess.Popen(['C:/Users/user/Downloads/window_toast_ms-main/window_toast_ms/dist/make_exe.exe'])  # EXE 파일 경로 설정
            self.label_status.setText('EXE 파일 실행 중...')
        except Exception as e:
            self.label_status.setText('EXE 파일 실행 실패: ' + str(e))


# PyQt5 애플리케이션 실행
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = MyApp()
    ex.show()
    sys.exit(app.exec_())
