# pip install PyQt5
# pip install PyQt5-tools
# pip install paramiko
# pip install matplotlib

import sys
import paramiko
import json
import threading
import queue
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTabWidget, QLabel, QPushButton, QLineEdit, QGroupBox, 
                           QFormLayout, QDateEdit, QTableWidget, QHBoxLayout, 
                           QTableWidgetItem, QMessageBox)
from PyQt5.QtCore import QTimer, QDate, pyqtSignal, QObject

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(MplCanvas, self).__init__(fig)
        fig.tight_layout()

class DataReceiver(QObject):
    data_received = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.data_queue = queue.Queue()
        self.running = False

    def start_receiving(self, ssh_client):
        self.running = True
        thread = threading.Thread(target=self._receive_data, args=(ssh_client,))
        thread.daemon = True
        thread.start()

    def stop_receiving(self):
        self.running = False

    def _receive_data(self, ssh_client):
        try:
            command = "python3 /home/pi/read_pressure.py"
            stdin, stdout, stderr = ssh_client.exec_command(command)
            
            while self.running:
                line = stdout.readline()
                if not line:
                    break
                try:
                    value = float(line.strip())
                    self.data_received.emit(value)
                except ValueError as e:
                    self.error_occurred.emit(f"데이터 변환 오류: {str(e)}")
        except Exception as e:
            self.error_occurred.emit(f"데이터 수신 오류: {str(e)}")

class DeviceInfo:
    def __init__(self):
        self.hostname = ""
        self.username = ""
        self.password = ""
        self.is_connected = False
        self.ssh_client = None
        self.data_receiver = DataReceiver()

    def connect(self):
        try:
            self.ssh_client = paramiko.SSHClient()
            self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.ssh_client.connect(self.hostname, username=self.username, password=self.password)
            
            sftp = self.ssh_client.open_sftp()
            try:
                with sftp.file('/home/pi/read_pressure.py', 'w') as f:
                    f.write('''
import serial
import time

ser = serial.Serial('/dev/ttyUSB0', 9600)  # 아두이노 연결 포트에 맞게 수정 필요

while True:
    if ser.in_waiting:
        line = ser.readline().decode('utf-8').strip()
        try:
            print(float(line))
        except ValueError:
            pass
    time.sleep(0.1)
''')
            finally:
                sftp.close()

            stdin, stdout, stderr = self.ssh_client.exec_command('pip3 install pyserial')
            stdout.channel.recv_exit_status()

            self.is_connected = True
            return True
        except Exception as e:
            print(f"연결 실패: {str(e)}")
            self.is_connected = False
            return False

    def start_data_collection(self):
        if self.is_connected:
            self.data_receiver.start_receiving(self.ssh_client)

    def stop_data_collection(self):
        self.data_receiver.stop_receiving()

    def disconnect(self):
        self.stop_data_collection()
        if self.ssh_client:
            self.ssh_client.close()
            self.is_connected = False

class PostureMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.device = DeviceInfo()
        self.pressure_data = []
        self.times = []  # 시간 데이터 저장용
        self.initUI()
        
        # 데이터 수신 시그널 연결
        self.device.data_receiver.data_received.connect(self.handle_new_data)
        self.device.data_receiver.error_occurred.connect(self.handle_error)
        
        # 그래프 업데이트 타이머
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_graph)
        self.update_timer.start(1000)  # 1초마다 업데이트

    def handle_new_data(self, value):
        current_time = len(self.pressure_data)
        self.pressure_data.append(value)
        self.times.append(current_time)
        
        # 60초 데이터만 유지
        if len(self.pressure_data) > 60:
            self.pressure_data.pop(0)
            self.times.pop(0)
            
        self.update_posture_status(value)
        self.log_posture_data(value)

    def handle_error(self, error_message):
        QMessageBox.warning(self, '오류', error_message)

    def update_posture_status(self, value):
        if value > 80:
            status = '불량 (너무 기대어 앉음)'
        elif value < 20:
            status = '불량 (너무 앞으로 숙임)'
        else:
            status = '양호'
        self.posture_status_label.setText(f'현재 자세: {status}')

    def log_posture_data(self, value):
        current_time = datetime.now().strftime('%H:%M:%S')
        status = '불량' if value > 80 or value < 20 else '양호'
        
        row_position = self.stats_table.rowCount()
        self.stats_table.insertRow(row_position)
        
        self.stats_table.setItem(row_position, 0, QTableWidgetItem(current_time))
        self.stats_table.setItem(row_position, 1, QTableWidgetItem(status))
        self.stats_table.setItem(row_position, 2, QTableWidgetItem(f'{value:.1f}'))

    def update_graph(self):
        if self.device.is_connected and self.pressure_data:
            self.canvas.axes.clear()
            self.canvas.axes.plot(self.times, self.pressure_data, 'b-')
            self.canvas.axes.set_xlim(max(0, len(self.pressure_data) - 60), max(60, len(self.pressure_data)))
            self.canvas.axes.set_ylim(0, 100)
            self.canvas.axes.set_xlabel('시간 (초)')
            self.canvas.axes.set_ylabel('압력')
            self.canvas.axes.grid(True)
            self.canvas.draw()

    def initUI(self):
        self.setWindowTitle('자세 교정 모니터링 시스템')
        self.setGeometry(100, 100, 1000, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        # 탭 위젯 생성
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # 장치 정보 탭
        device_tab = QWidget()
        device_layout = QVBoxLayout()
        
        self.status_label = QLabel('연결 상태: 미연결')
        device_layout.addWidget(self.status_label)

        connect_button = QPushButton('수동 연결')
        connect_button.clicked.connect(self.connect_device)
        device_layout.addWidget(connect_button)

        settings_group = QGroupBox('SSH 설정')
        settings_layout = QFormLayout()
        
        self.hostname_input = QLineEdit(self.device.hostname)
        self.username_input = QLineEdit(self.device.username)
        self.password_input = QLineEdit(self.device.password)
        self.password_input.setEchoMode(QLineEdit.Password)
        
        settings_layout.addRow('호스트:', self.hostname_input)
        settings_layout.addRow('사용자명:', self.username_input)
        settings_layout.addRow('비밀번호:', self.password_input)
        
        settings_group.setLayout(settings_layout)
        device_layout.addWidget(settings_group)
        
        device_tab.setLayout(device_layout)

        # 자세 분석 탭
        posture_tab = QWidget()
        posture_layout = QVBoxLayout()

        status_group = QGroupBox('현재 자세 상태')
        status_layout = QVBoxLayout()
        self.posture_status_label = QLabel('현재 자세: 분석 중...')
        status_layout.addWidget(self.posture_status_label)
        status_group.setLayout(status_layout)
        posture_layout.addWidget(status_group)

        graph_group = QGroupBox('압력 센서 데이터')
        graph_layout = QVBoxLayout()
        
        # Matplotlib 캔버스 생성
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        graph_layout.addWidget(self.canvas)
        
        graph_group.setLayout(graph_layout)
        posture_layout.addWidget(graph_group)
        
        posture_tab.setLayout(posture_layout)

        # 기록 및 통계 탭
        stats_tab = QWidget()
        stats_layout = QVBoxLayout()
        
        date_selector = QDateEdit()
        date_selector.setCalendarPopup(True)
        date_selector.setDate(QDate.currentDate())
        stats_layout.addWidget(date_selector)
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(['시간', '자세 상태', '압력값'])
        stats_layout.addWidget(self.stats_table)
        
        stats_tab.setLayout(stats_layout)

        # 탭 추가
        tabs.addTab(device_tab, '장치 정보')
        tabs.addTab(posture_tab, '자세 분석')
        tabs.addTab(stats_tab, '기록 및 통계')

        self.statusBar().showMessage('시스템 준비')

        # 자동 연결 시도
        QTimer.singleShot(1000, self.auto_connect)

    def connect_device(self):
        self.device.hostname = self.hostname_input.text()
        self.device.username = self.username_input.text()
        self.device.password = self.password_input.text()

        if self.device.connect():
            self.status_label.setText('연결 상태: 연결됨')
            self.statusBar().showMessage('장치 연결 성공')
            self.save_connection_settings()
            self.device.start_data_collection()
        else:
            self.status_label.setText('연결 상태: 연결 실패')
            self.statusBar().showMessage('장치 연결 실패')

    def auto_connect(self):
        try:
            with open('connection_settings.json', 'r') as f:
                settings = json.load(f)
                self.device.hostname = settings.get('hostname', self.device.hostname)
                self.device.username = settings.get('username', self.device.username)
                self.device.password = settings.get('password', self.device.password)
                
                self.hostname_input.setText(self.device.hostname)
                self.username_input.setText(self.device.username)
                self.password_input.setText(self.device.password)
                
                self.connect_device()
        except FileNotFoundError:
            self.statusBar().showMessage('저장된 연결 설정 없음')

    def save_connection_settings(self):
        settings = {
            'hostname': self.device.hostname,
            'username': self.device.username,
            'password': self.device.password
        }
        with open('connection_settings.json', 'w') as f:
            json.dump(settings, f)

    def closeEvent(self, event):
        self.device.disconnect()
        event.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PostureMonitorApp()
    ex.show()
    sys.exit(app.exec_())