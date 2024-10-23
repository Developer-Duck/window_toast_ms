# pyinstaller --onefile --windowed your_script.py
#pip install pyinstaller


from winotify import Notification

toast = Notification(
    app_id="로컬디스크 C",
    title="로컬디스크 C",
    msg="자세가 틀어졌습니다. 똑바로 앉아주세요",  # HTML 태그 제거
    icon="C:/Users/user/Downloads/window_toast_ms-main/window_toast_ms/images/warnning.ico",
    duration="short"
)

# 알림에 버튼 추가
toast.add_actions(
    label="올바르게 의자 앉는법", 
    launch="https://www.youtube.com/watch?v=3tCjbwNu9l0"  # 실제 유튜브 영상 ID로 교체
)

toast.show()