import os
import sys
from winotify import Notification

def resource_path(relative_path):
    """ Get the absolute path to the resource """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# 아이콘 파일 경로 설정
icon_path = resource_path("images/warnning.ico")

# 알림 설정
toast = Notification(
    app_id="로컬디스크 C",
    title="로컬디스크 C",
    msg="자세가 틀어졌습니다. 똑바로 앉아주세요",
    icon=icon_path,  # resource_path 함수를 이용한 경로 설정
    duration="short"
)

# 알림에 버튼 추가
toast.add_actions(
    label="올바르게 의자 앉는법",
    launch="https://www.youtube.com/watch?v=3tCjbwNu9l0"
)

# 알림 표시
toast.show()
