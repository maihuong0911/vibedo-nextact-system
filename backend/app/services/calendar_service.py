import os
import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.exceptions import RefreshError

# Quyền truy cập
SCOPES = ['https://www.googleapis.com/auth/calendar']

# ── Đường dẫn đến credentials.json ─────────────────────────────────────────
# Ưu tiên 1: biến môi trường GOOGLE_CRED_PATH (linh hoạt cho mọi môi trường)
# Ưu tiên 2: leo lên từ thư mục file hiện tại cho đến khi tìm thấy credentials.json
#             (tự động tìm trong backend/app/services/ → backend/app/ → backend/ → project root)
# Ưu tiên 3: fallback về cùng thư mục với file này

def _find_credentials() -> str:
    """Tự động tìm credentials.json từ thư mục hiện tại leo dần lên project root."""
    # Biến môi trường có độ ưu tiên cao nhất
    env_path = os.getenv("GOOGLE_CRED_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    # Leo từ thư mục file này lên tối đa 5 cấp
    cur = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        candidate = os.path.join(cur, 'credentials.json')
        if os.path.exists(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:   # đã đến filesystem root
            break
        cur = parent

    # Fallback: trả về đường dẫn cùng thư mục để thông báo lỗi rõ ràng
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'credentials.json')


def _find_token() -> str:
    """Đặt token.json cùng chỗ với credentials.json để dễ quản lý."""
    cred = _find_credentials()
    return os.path.join(os.path.dirname(cred), 'token.json')


CRED_PATH  = _find_credentials()
TOKEN_PATH = _find_token()


def _delete_token():
    """Xóa token.json khi token bị revoke để buộc re-auth."""
    if os.path.exists(TOKEN_PATH):
        os.remove(TOKEN_PATH)
        print("🗑️  [Calendar] Đã xóa token.json cũ.")


def get_calendar_service():
    """Lấy Google Calendar service với cơ chế tự động re-auth."""
    if not os.path.exists(CRED_PATH):
        # Thông báo lỗi rõ ràng nếu Hương quên chưa đổi tên hoặc để sai chỗ
        raise FileNotFoundError(f" Không tìm thấy credentials.json tại: {CRED_PATH}. Hãy đảm bảo file nằm cùng thư mục với code.")

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError:
                print("⚠️  Refresh token hết hạn. Đang yêu cầu đăng nhập lại...")
                _delete_token()
                creds = None
        
        if not creds:
            flow = InstalledAppFlow.from_client_secrets_file(CRED_PATH, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
        print(" [Calendar] Đã lưu token mới thành công.")

    return build('calendar', 'v3', credentials=creds)


def add_event_to_calendar(
    title: str,
    date_str: str | None,
    description: str = "",
    attendees_list: list[str] | None = None,
    notify_list: list[str] | None = None,
    reminder_mins: int | None = None,
) -> dict:
    """
    Thêm sự kiện vào Google Calendar với hỗ trợ:
    - attendees_list : tất cả người tham gia
    - notify_list    : chỉ những người cần nhận email mời (nằm trong notify_list)
    - reminder_mins  : số phút nhắc trước (linh hoạt theo nội dung AI trích xuất)
    """
    if not date_str:
        return {"success": False, "error": "Không có ngày giờ"}

    attendees_list = attendees_list or []
    notify_list    = notify_list or []
    notify_set     = set(notify_list)

    # reminder_mins mặc định 30 nếu không truyền vào
    if reminder_mins is None:
        reminder_mins = 30

    try:
        service = get_calendar_service()

        # ── Xử lý thời gian ─────────────────────────────────────────
        if isinstance(date_str, str) and 'T' in date_str:
            start = {'dateTime': date_str, 'timeZone': 'Asia/Ho_Chi_Minh'}
            dt = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            end_dt = dt + datetime.timedelta(hours=1)
            end = {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Ho_Chi_Minh'}
        else:
            date_only = date_str[:10]
            start = {'date': date_only, 'timeZone': 'Asia/Ho_Chi_Minh'}
            end   = {'date': date_only, 'timeZone': 'Asia/Ho_Chi_Minh'}

        # ── Xây dựng danh sách attendees ────────────────────────────
        # Chỉ thêm vào event những người có email hợp lệ
        # Mỗi attendee: responseRequested=True nếu trong notify_list
        attendee_objs = []
        for person in attendees_list:
            person = person.strip()
            if not person:
                continue
            # Kiểm tra xem có phải email không (đơn giản)
            is_email = "@" in person and "." in person.split("@")[-1]
            if not is_email:
                # Tên thường → bỏ qua (Google Calendar chỉ chấp nhận email)
                continue
            in_notify = person in notify_set
            attendee_objs.append({
                "email": person,
                "responseRequested": in_notify,  # True → Google gửi email mời
            })

        # ── Cấu hình reminders linh hoạt ────────────────────────────
        reminders_config = {
            'useDefault': False,
            'overrides': [
                {'method': 'popup', 'minutes': reminder_mins},
            ]
        }
        # Thêm email reminder nếu có notify_list (hoặc reminder quan trọng ≥ 60p)
        if notify_list or reminder_mins >= 60:
            reminders_config['overrides'].append(
                {'method': 'email', 'minutes': reminder_mins}
            )

        # ── sendUpdates: 'all' nếu có notify_list, ngược lại 'none' ─
        send_updates = 'all' if notify_list else 'none'

        event_body = {
            'summary':     title[:100],
            'description': description or "Được tạo tự động bởi NextAct AI",
            'start':       start,
            'end':         end,
            'reminders':   reminders_config,
        }
        if attendee_objs:
            event_body['attendees'] = attendee_objs

        created_event = service.events().insert(
            calendarId='primary',
            body=event_body,
            sendUpdates=send_updates,
        ).execute()

        print(f" [Calendar] Đã tạo: {title} | attendees: {len(attendee_objs)} | sendUpdates: {send_updates} | reminder: {reminder_mins}p")
        return {
            "success":  True,
            "htmlLink": created_event.get('htmlLink'),
            "status":   "created",
        }

    except Exception as e:
        print(f" [Calendar] Lỗi: {str(e)}")
        return {"success": False, "error": str(e)}