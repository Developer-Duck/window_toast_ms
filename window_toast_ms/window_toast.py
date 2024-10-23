#pyinstaller --onefile --windowed your_script.py
#pip install pywin32

# 2-3. 서비스 설치
# 이제 위의 Python 스크립트를 Windows 서비스로 등록합니다. 먼저 .py 파일을 .exe 파일로 변환한 후, 다음 명령을 사용하여 서비스로 등록합니다:

# python your_service_script.py install

# python your_service_script.py start



import time
import servicemanager
import win32serviceutil
import win32service
import win32event

class MyService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MyPythonService"
    _svc_display_name_ = "Python Background Service"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.is_running = True

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        self.is_running = False

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE,
                              servicemanager.PYS_SERVICE_STARTED,
                              (self._svc_name_, ''))
        self.main()

    def main(self):
        while self.is_running:
            # 여기에 백그라운드에서 실행할 코드 작성
            time.sleep(5)

if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(MyService)
