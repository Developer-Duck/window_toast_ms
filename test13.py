import sys
import json
import socket
import threading
import queue
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                            QTabWidget, QLabel, QPushButton, QLineEdit, QGroupBox,
                            QFormLayout, QTableWidget, QHBoxLayout,
                            QTableWidgetItem, QMessageBox, QSpinBox, QCheckBox,
                            QFileDialog, QComboBox, QDoubleSpinBox, QScrollArea,
                            QGridLayout,QHeaderView,QFrame,QSizePolicy)
from PyQt5.QtCore import QTimer, QDate, pyqtSignal, QObject, Qt
from PyQt5.QtGui import QColor
import winreg
import os
import subprocess
import matplotlib.animation as animation

class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=2, height=1.5, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super().__init__(fig)
        fig.tight_layout()

class Settings:
    def __init__(self):
        self.settings_file = 'app_settings.json'
        self.stats_file = 'posture_stats.json'
        self.load_settings()

    def load_settings(self):
        try:
            with open(self.settings_file, 'r') as f:
                settings = json.load(f)
        except FileNotFoundError:
            settings = self.get_default_settings()
        
        self.autostart = settings.get('autostart', False)
        self.toast_interval = settings.get('toast_interval', 1)
        self.toast_app = settings.get('toast_app', '')
        self.bad_posture_app = settings.get('bad_posture_app', '')  # 추가
        self.host = settings.get('host', '')
        self.port = settings.get('port', 5000)
        self.saved_servers = settings.get('saved_servers', [])
        self.user_weight = settings.get('user_weight', 0.0)
        self.user_height = settings.get('user_height', 0.0)
        self.user_gender = settings.get('user_gender', '')
        self.user_age = settings.get('user_age', 0)
        self.bad_posture_alert_active = settings.get('bad_posture_alert_active', True)  # 추가

    def save_settings(self):
        settings = {
            'autostart': self.autostart,
            'toast_interval': self.toast_interval,
            'toast_app': self.toast_app,
            'bad_posture_app': self.bad_posture_app,  # 추가
            'bad_posture_alert_active': self.bad_posture_alert_active,  # 추가
            'host': self.host,
            'port': self.port,
            'saved_servers': self.saved_servers,
            'user_weight': self.user_weight,
            'user_height': self.user_height,
            'user_gender': self.user_gender,
            'user_age': self.user_age
        }
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f)

    def load_stats(self):
        """저장된 자세 기록 데이터 로드"""
        try:
            with open(self.stats_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save_stats(self, stats):
        """자세 기록 데이터 저장"""
        with open(self.stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)

    def get_default_settings(self):
        return {
            'autostart': False,
            'toast_interval': 1,
            'toast_app': '',
            'host': '',
            'port': 5000,
            'saved_servers': [],  # 추가
            'user_weight': 0.0,
            'user_height': 0.0,
            'user_gender': '',
            'user_age': 0
        }
    
    def add_saved_server(self, host, port):
        server = f"{host}:{port}"
        if server not in self.saved_servers:
            self.saved_servers.append(server)
            self.save_settings()
    
    def remove_saved_server(self, server):
        if server in self.saved_servers:
            self.saved_servers.remove(server)
            self.save_settings()

    def clear_saved_servers(self):
        self.saved_servers = []
        self.save_settings()
        

class DataReceiver(QObject):
    data_received = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.socket = None
        self.running = False

    def connect(self, host, port):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((host, port))
            return True
        except Exception as e:
            self.error_occurred.emit(str(e))
            return False

    def start_receiving(self):
        if self.socket:
            self.running = True
            thread = threading.Thread(target=self._receive_data)
            thread.daemon = True
            thread.start()

    def stop_receiving(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def _receive_data(self):
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(1024).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    try:
                        values = json.loads(line)
                        self.data_received.emit(values)
                    except (json.JSONDecodeError, KeyError, ValueError) as e:
                        self.error_occurred.emit(f"데이터 변환 오류: {str(e)}")
            except Exception as e:
                self.error_occurred.emit(f"데이터 수신 오류: {str(e)}")
                break

class PostureMonitorApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = Settings()
        self.data_receiver = DataReceiver()
        self.sensor_names = [
            "right_hip", "left_hip", "left_thigh1", "left_thigh2",
            "right_thigh1", "right_thigh2", "left_calf", "right_calf",
            "spine_bottom", "spine_top", "left_wing_bone", "right_wing_bone"
        ]
        self.pressure_data = {name: [] for name in self.sensor_names}
        self.times = []
        self.canvases = {}
        self.last_notification_time = datetime.now()
        self.notification_active = True
        self.max_data_points = 100
        self.current_start_index = 0
        self.stats_data = []  # 기록 데이터 저장용 리스트

        plt.rcParams['font.family'] = 'Malgun Gothic'

        self.initUI()
        self.load_saved_stats()  # 저장된 기록 불러오기
        self.showMaximized()
        
        self.data_receiver.data_received.connect(self.handle_new_data)
        self.data_receiver.error_occurred.connect(self.handle_error)
        
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_graphs)
        self.update_timer.start(1000)

        self.notification_timer = QTimer()
        self.notification_timer.timeout.connect(self.check_notification)
        self.notification_timer.start(1000)

    def load_saved_stats(self):
        """저장된 기록 불러오기"""
        stats = self.settings.load_stats()
        for stat in stats:
            row_position = self.stats_table.rowCount()
            self.stats_table.insertRow(row_position)
            
            self.stats_table.setItem(row_position, 0, QTableWidgetItem(stat['time']))
            self.stats_table.setItem(row_position, 1, QTableWidgetItem(stat['status']))
            self.stats_table.setItem(row_position, 2, QTableWidgetItem(stat['pressure']))
            
            # 상태에 따라 배경색 설정
            color = 'pink' if stat['status'] == '불량' else 'lightgreen'
            for col in range(3):
                self.stats_table.item(row_position, col).setBackground(QColor(color))

        
    def check_notification(self):
        if not self.notification_active or not self.settings.toast_app:
            return
            
        current_time = datetime.now()
        time_diff = (current_time - self.last_notification_time).total_seconds() / 60  # Convert to minutes
        
        if time_diff >= self.settings.toast_interval:
            self.show_notification()
            self.last_notification_time = current_time

    def show_notification(self):
        if self.settings.toast_app and os.path.exists(self.settings.toast_app):
            try:
                subprocess.Popen([self.settings.toast_app])
            except Exception as e:
                QMessageBox.warning(self, '알림 오류', f'알림 실행 실패: {str(e)}')

    def set_autostart(self, state):
        key = winreg.HKEY_CURRENT_USER
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "PostureMonitor"
        
        try:
            if state:
                key_handle = winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS)
                winreg.SetValueEx(key_handle, app_name, 0, winreg.REG_SZ, sys.argv[0])
            else:
                key_handle = winreg.OpenKey(key, key_path, 0, winreg.KEY_ALL_ACCESS)
                winreg.DeleteValue(key_handle, app_name)
            winreg.CloseKey(key_handle)
        except Exception as e:
            QMessageBox.warning(self, '자동 시작 설정 오류', str(e))

    def reset_graph_data(self):
        """그래프 데이터 초기화"""
        self.times = []
        self.current_start_index = 0
        self.pressure_data = {name: [] for name in self.sensor_names}
        
        # 모든 그래프 캔버스 초기화
        for sensor_name, canvas in self.canvases.items():
            canvas.axes.clear()
            canvas.axes.grid(True)
            canvas.axes.set_title("")
            canvas.axes.set_xlabel("")
            canvas.axes.set_ylabel("")
            canvas.axes.set_ylim(0, 1024)
            canvas
            canvas.draw()

    def handle_new_data(self, values):
        if len(self.times) >= self.max_data_points // 2:
            self.times = self.times[self.max_data_points // 4:]
            for sensor_name in self.sensor_names:
                if self.pressure_data[sensor_name]:
                    self.pressure_data[sensor_name] = self.pressure_data[sensor_name][self.max_data_points // 4:]
            self.current_start_index += self.max_data_points // 4
        
        current_time = self.current_start_index + len(self.times)
        self.times.append(current_time)
        
        total_pressure = 0
        for sensor_name in self.sensor_names:
            value = values.get(sensor_name, 0)
            self.pressure_data[sensor_name].append(value)
            total_pressure += value
        
        self.update_posture_status(total_pressure)
        self.log_posture_data(total_pressure)
    
    def update_graphs(self):
        if not self.data_receiver.socket:
            return
            
        for sensor_name, canvas in self.canvases.items():
            if self.pressure_data[sensor_name] and len(self.pressure_data[sensor_name]) > 0:
                canvas.axes.clear()
                
                x_data = self.times
                y_data = self.pressure_data[sensor_name]
                
                canvas.axes.plot(x_data, y_data, 'b-')
                
                canvas.axes.set_xlim(
                    self.current_start_index,
                    self.current_start_index + self.max_data_points // 2 + 10
                )
                canvas.axes.set_ylim(0, 1024)

                canvas.axes.grid(True)
                canvas.axes.set_title("")
                canvas.axes.set_xlabel("")
                canvas.axes.set_ylabel("")
                
                canvas.draw()

    def handle_error(self, error_message):
        QMessageBox.warning(self, '오류', error_message)

    def update_posture_status(self, total_pressure):
        if total_pressure >= 6000:
            status = '양호'
            color = 'green'
        else:
            status = '불량'
            color = 'red'
            # 나쁜 자세일 때 알림 실행
            if self.settings.bad_posture_alert_active and self.settings.bad_posture_app:
                try:
                    subprocess.Popen([self.settings.bad_posture_app])
                except Exception as e:
                    QMessageBox.warning(self, '알림 오류', f'나쁜 자세 알림 실행 실패: {str(e)}')
        
        self.posture_status_label.setText(f'현재 자세: {status} (총 압력: {total_pressure:.1f})')
        self.posture_status_label.setStyleSheet(f'color: {color}')

    def log_posture_data(self, total_pressure):
        current_time = datetime.now().strftime('%H:%M:%S')
        status = '불량' if total_pressure < 6000 else '양호'
        pressure_str = f'{total_pressure:.1f}'
        
        # 테이블에 데이터 추가
        row_position = self.stats_table.rowCount()
        self.stats_table.insertRow(row_position)
        
        self.stats_table.setItem(row_position, 0, QTableWidgetItem(current_time))
        self.stats_table.setItem(row_position, 1, QTableWidgetItem(status))
        self.stats_table.setItem(row_position, 2, QTableWidgetItem(pressure_str))

        # 상태에 따라 배경색 설정
        color = 'pink' if status == '불량' else 'lightgreen'
        for col in range(3):
            self.stats_table.item(row_position, col).setBackground(QColor(color))

        # 데이터 저장
        stat_entry = {
            'time': current_time,
            'status': status,
            'pressure': pressure_str
        }
        self.stats_data.append(stat_entry)
        self.settings.save_stats(self.stats_data)

    def update_server_table(self):
        """서버 테이블 업데이트"""
        self.server_table.setRowCount(0)
        
        for i, server in enumerate(self.settings.saved_servers):
            row_position = self.server_table.rowCount()
            self.server_table.insertRow(row_position)
            
            # 서버 주소
            server_item = QTableWidgetItem(server)
            server_item.setTextAlignment(Qt.AlignCenter)  # 텍스트 가운데 정렬
            
            # 짝수/홀수 행에 따라 다른 배경색 설정
            if i % 2 == 0:
                server_item.setBackground(QColor("#E8F5E9"))  # 연한 민트색
            else:
                server_item.setBackground(QColor("#F1F8E9"))  # 연한 라임색
                
            self.server_table.setItem(row_position, 0, server_item)
            
            # 삭제 버튼을 위한 위젯
            delete_button = QPushButton('삭제')
            # delete_button.setFixedWidth(200) 
            # delete_button.setFixedHeight(30) 
            delete_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            delete_button.clicked.connect(lambda checked, s=server: self.remove_server(s))
            
            # 버튼이 있는 셀도 같은 배경색 설정
            button_widget = QWidget()
            button_layout = QHBoxLayout(button_widget)
            button_layout.addWidget(delete_button)
            button_layout.setAlignment(Qt.AlignCenter)
            button_layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
            
            
            if i % 2 == 0:
                button_widget.setStyleSheet("background-color: #E8F5E9;")
            else:
                button_widget.setStyleSheet("background-color: #F1F8E9;")
                
            self.server_table.setCellWidget(row_position, 1, button_widget)

    def remove_server(self, server):
        """개별 서버 삭제"""
        reply = QMessageBox.question(self, '서버 삭제', 
                                f'서버 "{server}"를 삭제하시겠습니까?',
                                QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.settings.remove_saved_server(server)
            self.update_server_table()
            self.update_server_list()  # 콤보박스 업데이트
            self.statusBar().showMessage(f'서버 "{server}" 삭제됨')

    def clear_server_history(self):
        """모든 서버 기록 삭제"""
        if not self.settings.saved_servers:
            QMessageBox.information(self, '알림', '삭제할 서버 기록이 없습니다.')
            return

        reply = QMessageBox.question(self, '서버 기록 삭제', 
                                '모든 서버 기록을 삭제하시겠습니까?',
                                QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.settings.clear_saved_servers()
            self.update_server_table()
            self.update_server_list()  # 콤보박스 업데이트
            self.statusBar().showMessage('모든 서버 기록이 삭제되었습니다.')

            

    def browse_notification_app(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "알림 아이콘 선택",
            "",
            "실행 파일 (*.exe);;모든 파일 (*.*)"
        )
        if file_path:
            self.notification_app_path.setText(file_path)
            self.settings.toast_app = file_path
            self.settings.save_settings()

    def toggle_bad_posture_alert(self, state):
        self.settings.bad_posture_alert_active = bool(state)
        self.settings.save_settings()

    def browse_bad_posture_app(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "나쁜 자세 알림 프로그램 선택",
            "",
            "실행 파일 (*.exe);;모든 파일 (*.*)"
        )
        if file_path:
            self.bad_posture_app_path.setText(file_path)
            self.settings.bad_posture_app = file_path
            self.settings.save_settings()

    def initUI(self):
        self.setWindowTitle('자세 교정 모니터링 시스템')
        self.setGeometry(100, 100, 1000, 800)

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout()
        main_widget.setLayout(layout)

        self.setWindowState(Qt.WindowMaximized)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # 설정 탭
        settings_tab = QWidget()
        settings_layout = QVBoxLayout()

        # 테이블 높이 조절
        
        # 자동 시작 설정
        autostart_group = QGroupBox('시작 설정')
        autostart_layout = QVBoxLayout()
        self.autostart_checkbox = QCheckBox('윈도우 시작 시 자동 실행')
        self.autostart_checkbox.setChecked(self.settings.autostart)
        self.autostart_checkbox.stateChanged.connect(self.on_autostart_changed)
        autostart_layout.addWidget(self.autostart_checkbox)
        autostart_group.setLayout(autostart_layout)
        settings_layout.addWidget(autostart_group)
        
        # 서버 관리

        server_history_group = QGroupBox('서버 기록 관리')
        server_history_layout = QVBoxLayout()

        server_history_group.setLayout(server_history_layout)

        #높이 조절
        server_history_group.setFixedHeight(300)


        # 저장된 서버 목록을 보여주는 테이블
        self.server_table = QTableWidget()
        self.server_table.setColumnCount(2)
        self.server_table.setHorizontalHeaderLabels(['서버 주소', '동작'])
        self.server_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.server_table.verticalHeader().setVisible(False)
        self.server_table.setColumnWidth(1, 200)

        self.server_table.setAlternatingRowColors(True)
        server_history_layout.addWidget(self.server_table)

        self.update_server_table()


        clear_servers_button = QPushButton('모든 서버 기록 삭제')
        clear_servers_button.clicked.connect(self.clear_server_history)
        server_history_layout.addWidget(clear_servers_button)

        server_history_group.setLayout(server_history_layout)
        settings_layout.addWidget(server_history_group)
        

        # 알림 설정
        notification_group = QGroupBox('알림 설정')
        notification_layout = QFormLayout()
        
        self.notification_interval = QSpinBox()
        self.notification_interval.setRange(1, 60)
        self.notification_interval.setValue(self.settings.toast_interval)
        self.notification_interval.valueChanged.connect(self.on_interval_changed)
        notification_layout.addRow('알림 간격 (분):', self.notification_interval)

        self.notification_app_path = QLineEdit()
        self.notification_app_path.setText(self.settings.toast_app)
        browse_button = QPushButton('찾아보기')
        browse_button.clicked.connect(self.browse_notification_app)
        
        # 알림 활성화 체크박스 추가
        self.notification_active_checkbox = QCheckBox('알림 활성화')
        self.notification_active_checkbox.setChecked(True)
        self.notification_active_checkbox.stateChanged.connect(self.toggle_notification)
        notification_layout.addRow('알림 상태:', self.notification_active_checkbox)
    
        
        app_layout = QHBoxLayout()
        app_layout.addWidget(self.notification_app_path)
        app_layout.addWidget(browse_button)
        notification_layout.addRow('알림 프로그램:', app_layout)


        # 나쁜자세


        self.bad_posture_alert_checkbox = QCheckBox('나쁜 자세 알림 활성화')
        self.bad_posture_alert_checkbox.setChecked(self.settings.bad_posture_alert_active)
        self.bad_posture_alert_checkbox.stateChanged.connect(self.toggle_bad_posture_alert)
        notification_layout.addRow('나쁜 자세 알림 상태:', self.bad_posture_alert_checkbox)

        self.bad_posture_app_path = QLineEdit()
        self.bad_posture_app_path.setText(self.settings.bad_posture_app)
        bad_posture_browse_button = QPushButton('찾아보기')
        bad_posture_browse_button.clicked.connect(self.browse_bad_posture_app)
        
        bad_posture_app_layout = QHBoxLayout()
        bad_posture_app_layout.addWidget(self.bad_posture_app_path)
        bad_posture_app_layout.addWidget(bad_posture_browse_button)
        notification_layout.addRow('나쁜 자세 알림 프로그램:', bad_posture_app_layout)

        
        notification_group.setLayout(notification_layout)
        settings_layout.addWidget(notification_group)

        # 사용자 정보 설정
        user_info_group = QGroupBox('사용자 정보')
        user_info_layout = QFormLayout()

        self.user_weight = QDoubleSpinBox()
        self.user_weight.setRange(0.0, 300.0)
        self.user_weight.setValue(self.settings.user_weight)
        self.user_weight.valueChanged.connect(self.on_user_info_changed)
        user_info_layout.addRow('체중 (kg):', self.user_weight)

        self.user_height = QDoubleSpinBox()
        self.user_height.setRange(0.0, 200.0)
        self.user_height.setValue(self.settings.user_height)
        self.user_height.valueChanged.connect(self.on_user_info_changed)
        user_info_layout.addRow('키 (cm):', self.user_height)

        self.user_gender = QComboBox()
        self.user_gender.addItems(['', 'Male', 'Female'])
        self.user_gender.setCurrentText(self.settings.user_gender)
        self.user_gender.currentTextChanged.connect(self.on_user_info_changed)
        user_info_layout.addRow('성별:', self.user_gender)

        self.user_age = QSpinBox()
        self.user_age.setRange(0, 100)
        self.user_age.setValue(self.settings.user_age)
        self.user_age.valueChanged.connect(self.on_user_info_changed)
        user_info_layout.addRow('나이:', self.user_age)

        user_info_group.setLayout(user_info_layout)
        settings_layout.addWidget(user_info_group)
        
        settings_tab.setLayout(settings_layout)

        # 기존 탭들
        device_tab = self.create_device_tab()
        posture_tab = self.create_posture_tab()
        stats_tab = self.create_stats_tab()

        # 탭 추가
        tabs.addTab(device_tab, '장치 정보')
        tabs.addTab(posture_tab, '자세 분석')
        tabs.addTab(stats_tab, '기록 및 통계')
        tabs.addTab(settings_tab, '설정')

    def toggle_notification(self, state):
        self.notification_active = bool(state)
        if state:
            self.last_notification_time = datetime.now()  # 활성화시 타이머 리셋

    def on_autostart_changed(self, state):
        self.settings.autostart = bool(state)
        self.set_autostart(bool(state))
        self.settings.save_settings()

    def on_interval_changed(self, value):
        self.settings.toast_interval = value
        self.settings.save_settings()
        self.last_notification_time = datetime.now()  # 간격 변경시 타이머 리셋

    def on_user_info_changed(self):
        self.settings.user_weight = self.user_weight.value()
        self.settings.user_height = self.user_height.value()
        self.settings.user_gender = self.user_gender.currentText()
        self.settings.user_age = self.user_age.value()
        self.settings.save_settings()

    def create_device_tab(self):
        device_tab = QWidget()
        device_layout = QVBoxLayout()
        
        status_group = QGroupBox('연결 상태')
        status_layout = QVBoxLayout()
        self.status_label = QLabel('연결 상태: 미연결')
        status_layout.addWidget(self.status_label)
        status_group.setLayout(status_layout)
        device_layout.addWidget(status_group)

        settings_group = QGroupBox('연결 설정')
        settings_layout = QFormLayout()

        self.server_combo = QComboBox()
        self.server_combo.setEditable(True)
        self.update_server_list()
        self.server_combo.currentTextChanged.connect(self.on_server_selected)
        
        self.hostname_input = QLineEdit()
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(self.settings.port)
        
        settings_layout.addRow('저장된 서버:', self.server_combo)
        settings_layout.addRow('서버 주소:', self.hostname_input)
        settings_layout.addRow('포트:', self.port_input)
        
        settings_group.setLayout(settings_layout)
        device_layout.addWidget(settings_group)

        buttons_layout = QHBoxLayout()
        connect_button = QPushButton('연결')
        connect_button.clicked.connect(self.connect_device)
        disconnect_button = QPushButton('연결 해제')
        disconnect_button.clicked.connect(self.disconnect_device)
        
        buttons_layout.addWidget(connect_button)
        buttons_layout.addWidget(disconnect_button)
        device_layout.addLayout(buttons_layout)
        
        device_tab.setLayout(device_layout)
        return device_tab

    def update_server_list(self):
        self.server_combo.clear()
        self.server_combo.addItem('')  # 빈 항목 추가
        for server in self.settings.saved_servers:
            self.server_combo.addItem(server)

    def on_server_selected(self, server_str):
        if server_str:
            try:
                host, port = server_str.split(':')
                self.hostname_input.setText(host)
                self.port_input.setValue(int(port))
            except:
                pass

    def create_posture_tab(self):
        posture_tab = QWidget()
        main_layout = QVBoxLayout()

        # 상태 그룹
        status_group = QGroupBox('현재 자세 상태')
        status_layout = QVBoxLayout()
        self.posture_status_label = QLabel('현재 자세: 분석 중...')
        status_layout.addWidget(self.posture_status_label)
        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group)

        # 스크롤 영역 생성
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        graph_widget = QWidget()
        graph_layout = QGridLayout()

        # 그래프 생성
        row = 0
        col = 0
        for sensor_name in self.sensor_names:
            group = QGroupBox(f'{sensor_name} 압력')
            group_layout = QVBoxLayout()
            
            canvas = MplCanvas(self, width=4, height=3, dpi=100)
            self.canvases[sensor_name] = canvas
            # 초기 그래프 설정
            canvas.axes.grid(True)
            canvas.axes.set_ylim(0, 1024)
            canvas.draw()
            
            group_layout.addWidget(canvas)
            
            group.setLayout(group_layout)
            graph_layout.addWidget(group, row, col)
            
            col += 1
            if col > 2:  # 3열로 표시
                col = 0
                row += 1

        graph_widget.setLayout(graph_layout)
        scroll.setWidget(graph_widget)
        main_layout.addWidget(scroll)
        
        posture_tab.setLayout(main_layout)
        return posture_tab

    def create_stats_tab(self):
        stats_tab = QWidget()
        stats_layout = QVBoxLayout()
        
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(3)
        self.stats_table.setHorizontalHeaderLabels(['시간', '자세 상태', '압력값'])
        self.stats_table.horizontalHeader().setStretchLastSection(True)
        self.stats_table.setAlternatingRowColors(True)
        stats_layout.addWidget(self.stats_table)
        
        stats_buttons_layout = QHBoxLayout()
        export_button = QPushButton('데이터 내보내기')
        export_button.clicked.connect(self.export_data)
        clear_button = QPushButton('기록 지우기')
        clear_button.clicked.connect(self.clear_stats)
        stats_buttons_layout.addWidget(export_button)
        stats_buttons_layout.addWidget(clear_button)
        stats_layout.addLayout(stats_buttons_layout)
        
        stats_tab.setLayout(stats_layout)
        return stats_tab

    def connect_device(self):
        host = self.hostname_input.text()
        port = self.port_input.value()

        if not host:
            QMessageBox.warning(self, '입력 오류', '서버 주소를 입력해주세요.')
            return

        self.statusBar().showMessage('연결 시도 중...')
        
        if self.data_receiver.connect(host, port):
            self.status_label.setText('연결 상태: 연결됨')
            self.status_label.setStyleSheet('color: green')
            self.statusBar().showMessage('서버 연결 성공')
            
            self.settings.host = host
            self.settings.port = port
            self.settings.add_saved_server(host, port)
            self.settings.save_settings()
            
            # 서버 목록 업데이트
            self.update_server_list()
            self.update_server_table()
            
            self.data_receiver.start_receiving()
        else:
            self.status_label.setText('연결 상태: 연결 실패')
            self.status_label.setStyleSheet('color: red')
            self.statusBar().showMessage('서버 연결 실패')

    def disconnect_device(self):
        self.data_receiver.stop_receiving()
        self.status_label.setText('연결 상태: 미연결')
        self.status_label.setStyleSheet('color: black')
        self.posture_status_label.setText('현재 자세: 분석 중...')  # 자세 상태 레이블 초기화
        self.posture_status_label.setStyleSheet('color: black')  # 자세 상태 색상 초기화
        self.statusBar().showMessage('서버 연결 해제됨')
        self.reset_graph_data()  # 그래프 데이터 초기화

    def export_data(self):
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "데이터 내보내기",
                f'posture_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                "CSV 파일 (*.csv);;모든 파일 (*.*)"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write('시간,자세 상태,압력값\n')
                    for stat in self.stats_data:
                        f.write(f'{stat["time"]},{stat["status"]},{stat["pressure"]}\n')
                QMessageBox.information(self, '내보내기 성공', f'데이터가 {filename}에 저장되었습니다.')
        except Exception as e:
            QMessageBox.warning(self, '내보내기 실패', f'데이터 내보내기 실패: {str(e)}')

    def clear_stats(self):
        reply = QMessageBox.question(self, '기록 삭제', 
                                   '모든 기록을 삭제하시겠습니까?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.stats_table.setRowCount(0)
            self.stats_data = []  # 데이터 리스트 초기화
            self.settings.save_stats(self.stats_data)  # 빈 데이터 저장
            self.statusBar().showMessage('기록이 삭제되었습니다.')

    def closeEvent(self, event):
        reply = QMessageBox.question(self, '종료', 
                                   '프로그램을 종료하시겠습니까?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.data_receiver.stop_receiving()
            self.settings.save_settings()
            self.settings.save_stats(self.stats_data)  # 종료 시 기록 저장
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    
    # 프로그램이 이미 실행 중인지 확인
    socket_test = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        socket_test.bind(("localhost", 12345))  # 테스트용 포트
    except socket.error:
        QMessageBox.warning(None, '실행 오류', '프로그램이 이미 실행 중입니다.')
        return
    finally:
        socket_test.close()
    
    ex = PostureMonitorApp()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()