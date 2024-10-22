from winotify import Notification

toast = Notification(
    app_id="자세교정 AI",
    title="자세교정 AI",
    msg="<b>너무 오랫동안 앉아 있었습니다.</b>\n<i>휴식이나 스트레칭을 권장 합니다.</i>",  # HTML 태그 사용
    icon="C:/Users/user/Desktop/window_toast_massage/window_toast_ms/images/warnning.ico",
    duration="short"
)

# 알림에 버튼 추가도 가능합니다
toast.add_actions(label="스트레칭 방법 보기", launch="https://www.youtube.com/watch?v=MTU4iCDntjs&t=191s")

toast.show()