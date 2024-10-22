import paramiko
import tkinter as tk
from tkinter import messagebox

# SSH 클라이언트 초기화
ssh = None

def connect():
    global ssh  # 전역 변수로 SSH 클라이언트 사용
    ip = entry_ip.get()
    user = entry_user.get()
    passwd = entry_pass.get()

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        ssh.connect(ip, username=user, password=passwd)
        messagebox.showinfo("정보", f"{ip}에 성공적으로 연결되었습니다!")
        status_label.config(text=f"연결됨: {ip}")  # 연결 상태 업데이트
    except Exception as e:
        messagebox.showerror("오류", f"연결 오류: {e}")

def disconnect():
    global ssh
    if ssh is not None:
        ssh.close()
        status_label.config(text="연결 해제됨")  # 연결 해제 상태 업데이트
        messagebox.showinfo("정보", "연결이 해제되었습니다.")
    else:
        messagebox.showwarning("경고", "연결되지 않았습니다.")

# GUI 생성
window = tk.Tk()
window.title("Raspberry Pi 연결")

# 입력 필드 생성
tk.Label(window, text="IP 주소:").grid(row=0, column=0)
entry_ip = tk.Entry(window)
entry_ip.grid(row=0, column=1)

tk.Label(window, text="사용자 이름:").grid(row=1, column=0)
entry_user = tk.Entry(window)
entry_user.grid(row=1, column=1)

tk.Label(window, text="비밀번호:").grid(row=2, column=0)
entry_pass = tk.Entry(window, show="*")
entry_pass.grid(row=2, column=1)

# 버튼 생성
tk.Button(window, text="연결", command=connect).grid(row=3, column=0)
tk.Button(window, text="연결 취소", command=disconnect).grid(row=3, column=1)

# 연결 상태 레이블
status_label = tk.Label(window, text="연결되지 않음")  # 초기 상태
status_label.grid(row=4, columnspan=2)

# GUI 루프 실행
window.mainloop()