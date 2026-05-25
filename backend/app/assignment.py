"""
assignment.py
API endpoints cho 2 nhãn ưu tiên cao:
  - Giao việc    : giao task cho user khác, thông báo, xác nhận/từ chối
  - Lên lịch họp : mời nhiều người, thông báo, xác nhận/từ chối, Google Calendar

Đăng ký trong main.py:
    from backend.app import assignment
    app.include_router(assignment.router)
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

from .database import SessionLocal
from .models import Note, User, TaskAssignment, Notification
from .dependencies import get_current_user

router = APIRouter(tags=["assignment"])


# ── DB session ────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Email helper ──────────────────────────────────────────────────────
SMTP_HOST     = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER", "")          # Gmail của bạn
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")      # App password Gmail


def send_email(to_email: str, subject: str, body_html: str):
    """Gửi email qua Gmail SMTP. Không crash nếu thiếu cấu hình."""
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[Email] SMTP chưa cấu hình — bỏ qua gửi mail tới {to_email}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = SMTP_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(body_html, "html", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        print(f"[Email]  Đã gửi tới {to_email}: {subject}")
        return True
    except Exception as e:
        print(f"[Email]  Lỗi gửi mail: {e}")
        return False


# ── Schemas ───────────────────────────────────────────────────────────
class AssignTaskRequest(BaseModel):
    note_id: int                    # ID task/note đã tạo
    receiver_ids: List[int]         # Danh sách user_id nhận việc
    message: Optional[str] = ""    # Tin nhắn kèm theo (tuỳ chọn)
    assignment_type: str = "task"   # "task" hoặc "meeting"


class RespondAssignmentRequest(BaseModel):
    action: str   # "accepted" hoặc "rejected"


# =====================================================================
# GET /users/list — lấy danh sách user để hiển thị dropdown chọn người
# =====================================================================
@router.get("/users/list")
def get_users_list(request: Request, db: Session = Depends(get_db)):
    """
    Trả về danh sách tất cả user trong hệ thống (trừ bản thân).
    Frontend dùng để hiển thị dropdown chọn người nhận task / người mời họp.
    """
    current_user_id = get_current_user(request)
    users = db.query(User).filter(User.id != current_user_id).all()
    return [
        {
            "id":        u.id,
            "full_name": u.full_name,
            "email":     u.email,
        }
        for u in users
    ]


# =====================================================================
# POST /assignments/assign — giao task / mời họp cho người khác
# =====================================================================
@router.post("/assignments/assign")
def assign_task(
    payload: AssignTaskRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Giao task (nhãn Giao việc) hoặc mời họp (nhãn Lên lịch họp)
    cho một hoặc nhiều người dùng khác.

    Flow:
    1. Kiểm tra note tồn tại và thuộc sender
    2. Tạo TaskAssignment cho từng receiver
    3. Tạo Notification cho từng receiver
    4. Gửi email thông báo cho từng receiver
    """
    sender_id = get_current_user(request)
    sender    = db.query(User).filter(User.id == sender_id).first()

    # Kiểm tra note tồn tại
    note = db.query(Note).filter(
        Note.id == payload.note_id,
        Note.user_id == sender_id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="Task không tồn tại hoặc không có quyền giao")

    if not payload.receiver_ids:
        raise HTTPException(status_code=400, detail="Cần chọn ít nhất 1 người nhận")

    is_meeting = payload.assignment_type == "meeting"
    created    = []

    for receiver_id in payload.receiver_ids:
        receiver = db.query(User).filter(User.id == receiver_id).first()
        if not receiver:
            continue

        # Tạo assignment
        assignment = TaskAssignment(
            note_id         = note.id,
            sender_id       = sender_id,
            receiver_id     = receiver_id,
            assignment_type = payload.assignment_type,
            status          = "pending",
            message         = payload.message or "",
        )
        db.add(assignment)
        db.flush()  # lấy assignment.id

        # Tạo notification cho receiver
        if is_meeting:
            notif_title = f" {sender.full_name} mời bạn tham gia cuộc họp"
            notif_body  = f'Cuộc họp: "{note.title}"'
            if note.due_date:
                notif_body += f"\n Thời gian: {note.due_date.strftime('%d/%m/%Y %H:%M')}"
        else:
            notif_title = f" {sender.full_name} giao việc cho bạn"
            notif_body  = f'Công việc: "{note.title}"'
            if note.due_date:
                notif_body += f"\n Hạn chót: {note.due_date.strftime('%d/%m/%Y %H:%M')}"

        if payload.message:
            notif_body += f"\n Ghi chú: {payload.message}"

        notif = Notification(
            user_id       = receiver_id,
            sender_id     = sender_id,
            type          = "meeting_invited" if is_meeting else "task_assigned",
            title         = notif_title,
            body          = notif_body,
            assignment_id = assignment.id,
            note_id       = note.id,
            is_read       = False,
        )
        db.add(notif)

        # Gửi email
        _send_assignment_email(
            to_email    = receiver.email,
            to_name     = receiver.full_name,
            sender_name = sender.full_name,
            note        = note,
            assignment  = assignment,
            message     = payload.message or "",
            is_meeting  = is_meeting,
        )

        created.append({
            "assignment_id": assignment.id,
            "receiver_id":   receiver_id,
            "receiver_name": receiver.full_name,
        })

    db.commit()

    action_word = "mời họp" if is_meeting else "giao việc"
    return {
        "success": True,
        "message": f"Đã {action_word} cho {len(created)} người",
        "assignments": created,
    }


# =====================================================================
# POST /assignments/{id}/respond — xác nhận hoặc từ chối
# =====================================================================
@router.post("/assignments/{assignment_id}/respond")
def respond_assignment(
    assignment_id: int,
    payload: RespondAssignmentRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Người nhận nhấn "Xác nhận" hoặc "Từ chối" từ thông báo.

    Nếu Xác nhận:
    - Tạo Note mới trong Công việc của người nhận (copy từ note gốc)
    - Nếu là cuộc họp: thêm vào Google Calendar của người nhận
    - Gửi thông báo ngược lại cho người giao việc

    Nếu Từ chối:
    - Cập nhật assignment status = rejected
    - Gửi thông báo cho người giao việc
    """
    current_user_id = get_current_user(request)

    if payload.action not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="action phải là 'accepted' hoặc 'rejected'")

    assignment = db.query(TaskAssignment).filter(
        TaskAssignment.id          == assignment_id,
        TaskAssignment.receiver_id == current_user_id,
        TaskAssignment.status      == "pending"
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Không tìm thấy yêu cầu hoặc đã xử lý rồi")

    # Lấy thông tin liên quan
    original_note = db.query(Note).filter(Note.id == assignment.note_id).first()
    sender        = db.query(User).filter(User.id == assignment.sender_id).first()
    receiver      = db.query(User).filter(User.id == current_user_id).first()
    is_meeting    = assignment.assignment_type == "meeting"

    # Cập nhật status
    assignment.status      = payload.action
    assignment.responded_at = datetime.now()

    calendar_link = None

    if payload.action == "accepted":
        # Tạo Note mới trong Công việc của receiver
        new_note = Note(
            user_id   = current_user_id,
            title     = original_note.title,
            content   = (
                f"[Được giao bởi {sender.full_name}]\n"
                + (f"{assignment.message}\n" if assignment.message else "")
                + (original_note.content or "")
            ),
            status    = "todo",
            priority  = original_note.priority,
            due_date  = original_note.due_date,
            label     = original_note.label,
            is_quick_add = False,
        )
        db.add(new_note)
        db.flush()

        # Nếu là cuộc họp → thêm Google Calendar
        if is_meeting and original_note.due_date:
            try:
                from .services.calendar_service import add_event_to_calendar
                cal_result = add_event_to_calendar(
                    title       = original_note.title,
                    date_str    = original_note.due_date.isoformat(),
                    description = (
                        f"Cuộc họp do {sender.full_name} tổ chức\n"
                        f"{assignment.message or ''}"
                    )
                )
                if cal_result.get("success"):
                    calendar_link = cal_result.get("htmlLink")
            except Exception as e:
                print(f"[Assignment] Calendar error: {e}")

        # Thông báo cho SENDER: receiver đã chấp nhận
        notif_back = Notification(
            user_id       = assignment.sender_id,
            sender_id     = current_user_id,
            type          = "task_accepted",
            title         = f" {receiver.full_name} đã chấp nhận {'cuộc họp' if is_meeting else 'công việc'}",
            body          = f'"{original_note.title}"',
            assignment_id = assignment.id,
            note_id       = assignment.note_id,
        )
        db.add(notif_back)

        # Email xác nhận cho sender
        send_email(
            to_email   = sender.email,
            subject    = f" {receiver.full_name} đã xác nhận {'tham gia họp' if is_meeting else 'nhận việc'}",
            body_html  = f"""
<p>Xin chào <b>{sender.full_name}</b>,</p>
<p><b>{receiver.full_name}</b> đã <span style="color:green"><b>xác nhận {'tham gia cuộc họp' if is_meeting else 'nhận công việc'}</b></span>:</p>
<blockquote style="border-left:3px solid green;padding-left:12px">
  <b>{original_note.title}</b>
  {'<br>⏰ ' + original_note.due_date.strftime('%d/%m/%Y %H:%M') if original_note.due_date else ''}
</blockquote>
<p style="color:#555">— NextAct System</p>
"""
        )

        action_text = "chấp nhận tham gia cuộc họp" if is_meeting else "chấp nhận công việc"

    else:  # rejected
        # Thông báo cho SENDER: receiver từ chối
        notif_back = Notification(
            user_id       = assignment.sender_id,
            sender_id     = current_user_id,
            type          = "task_rejected",
            title         = f" {receiver.full_name} đã từ chối {'cuộc họp' if is_meeting else 'công việc'}",
            body          = f'"{original_note.title}"',
            assignment_id = assignment.id,
            note_id       = assignment.note_id,
        )
        db.add(notif_back)

        send_email(
            to_email   = sender.email,
            subject    = f" {receiver.full_name} từ chối {'tham gia họp' if is_meeting else 'nhận việc'}",
            body_html  = f"""
<p>Xin chào <b>{sender.full_name}</b>,</p>
<p><b>{receiver.full_name}</b> đã <span style="color:red"><b>từ chối {'tham gia cuộc họp' if is_meeting else 'nhận công việc'}</b></span>:</p>
<blockquote style="border-left:3px solid red;padding-left:12px">
  <b>{original_note.title}</b>
</blockquote>
<p style="color:#555">— NextAct System</p>
"""
        )
        action_text = "từ chối"

    db.commit()
    return {
        "success":       True,
        "action":        payload.action,
        "message":       f"Đã {action_text} thành công",
        "calendar_link": calendar_link,
    }


# =====================================================================
# GET /notifications — lấy thông báo của user hiện tại
# =====================================================================
@router.get("/notifications")
def get_notifications(request: Request, db: Session = Depends(get_db)):
    """
    Trả về danh sách thông báo của user hiện tại, mới nhất trước.
    Frontend dùng để hiển thị dropdown icon 🔔.
    """
    user_id = get_current_user(request)
    notifs  = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(30)
        .all()
    )
    unread = sum(1 for n in notifs if not n.is_read)

    # Lấy assignment status cho các thông báo có assignment_id
    assignment_ids = [n.assignment_id for n in notifs if n.assignment_id]
    assignment_status_map = {}
    if assignment_ids:
        assignments = db.query(TaskAssignment).filter(TaskAssignment.id.in_(assignment_ids)).all()
        assignment_status_map = {a.id: a.status for a in assignments}

    return {
        "unread_count": unread,
        "notifications": [
            {
                "id":                n.id,
                "type":              n.type,
                "title":             n.title,
                "body":              n.body,
                "is_read":           n.is_read,
                "assignment_id":     n.assignment_id,
                "assignment_status": assignment_status_map.get(n.assignment_id) if n.assignment_id else None,
                "note_id":           n.note_id,
                "created_at":        n.created_at.isoformat() if n.created_at else None,
            }
            for n in notifs
        ]
    }


# =====================================================================
# PUT /notifications/{id}/read — đánh dấu đã đọc
# =====================================================================
@router.put("/notifications/{notif_id}/read")
def mark_read(notif_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    n = db.query(Notification).filter(
        Notification.id      == notif_id,
        Notification.user_id == user_id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông báo")
    n.is_read = True
    db.commit()
    return {"success": True}


# =====================================================================
# PUT /notifications/read-all — đánh dấu tất cả đã đọc
# =====================================================================
@router.put("/notifications/read-all")
def mark_all_read(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return {"success": True}


# =====================================================================
# GET /assignments/pending — lấy danh sách assignment đang chờ xử lý
# =====================================================================
@router.get("/assignments/pending")
def get_pending_assignments(request: Request, db: Session = Depends(get_db)):
    """Danh sách task/cuộc họp đang chờ receiver xác nhận."""
    user_id     = get_current_user(request)
    assignments = (
        db.query(TaskAssignment)
        .filter(
            TaskAssignment.receiver_id == user_id,
            TaskAssignment.status      == "pending"
        )
        .order_by(TaskAssignment.created_at.desc())
        .all()
    )
    result = []
    for a in assignments:
        note   = db.query(Note).filter(Note.id == a.note_id).first()
        sender = db.query(User).filter(User.id == a.sender_id).first()
        if not note or not sender:
            continue
        result.append({
            "assignment_id":   a.id,
            "type":            a.assignment_type,
            "note_id":         note.id,
            "note_title":      note.title,
            "note_due_date":   note.due_date.isoformat() if note.due_date else None,
            "sender_id":       sender.id,
            "sender_name":     sender.full_name,
            "message":         a.message,
            "created_at":      a.created_at.isoformat() if a.created_at else None,
        })
    return result


# ── Email template helper (dùng nội bộ) ──────────────────────────────
def _send_assignment_email(
    to_email:    str,
    to_name:     str,
    sender_name: str,
    note:        Note,
    assignment:  TaskAssignment,
    message:     str,
    is_meeting:  bool,
):
    action_word  = "mời bạn tham gia cuộc họp" if is_meeting else "giao công việc cho bạn"
    type_label   = "Cuộc họp" if is_meeting else "Công việc"
    due_str      = note.due_date.strftime("%d/%m/%Y %H:%M") if note.due_date else "Chưa xác định"
    base_url     = os.getenv("APP_BASE_URL", "http://127.0.0.1:8002")

    body_html = f"""
<div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden">
  <div style="background:#196B7C;padding:20px 24px">
    <h2 style="color:#fff;margin:0">NextAct — Thông báo mới</h2>
  </div>
  <div style="padding:24px">
    <p>Xin chào <b>{to_name}</b>,</p>
    <p><b>{sender_name}</b> đã <b>{action_word}</b>:</p>

    <div style="background:#f5f5f5;border-left:4px solid #196B7C;padding:12px 16px;border-radius:4px;margin:16px 0">
      <p style="margin:0 0 6px"><b>{type_label}:</b> {note.title}</p>
      <p style="margin:0 0 6px"><b> Thời gian/Hạn chót:</b> {due_str}</p>
      {'<p style="margin:0"><b> Ghi chú:</b> ' + message + '</p>' if message else ''}
    </div>

    <p>Vui lòng xem và phản hồi trong hệ thống NextAct:</p>

    <div style="text-align:center;margin:20px 0">
      <a href="{base_url}/tasks" style="background:#196B7C;color:#fff;padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:bold;margin-right:10px">
         Xác nhận
      </a>
      <a href="{base_url}/tasks" style="background:#e05252;color:#fff;padding:10px 24px;border-radius:6px;text-decoration:none;font-weight:bold">
         Từ chối
      </a>
    </div>

    <p style="color:#999;font-size:12px">
      Hoặc vào <a href="{base_url}/tasks">{base_url}/tasks</a> → icon 🔔 để phản hồi.
    </p>
  </div>
  <div style="background:#f9f9f9;padding:12px 24px;text-align:center;color:#aaa;font-size:11px">
    NextAct — Hệ thống gợi ý hành động tiếp theo từ văn bản
  </div>
</div>
"""
    subject = (
        f"{sender_name} mời bạn tham gia cuộc họp: {note.title}"
        if is_meeting
        else f"{sender_name} giao việc cho bạn: {note.title}"
    )
    send_email(to_email=to_email, subject=subject, body_html=body_html)

# =====================================================================
# GET /stats — Thống kê tổng hợp cho trang Home
# =====================================================================
@router.get("/stats")
def get_stats(request: Request, db: Session = Depends(get_db)):
    """
    Trả về số liệu thống kê cho dashboard:
    - Tổng task (của user), theo status
    - Task đã giao đi (sender) và nhận về (receiver), theo status
    - Phân bổ theo nhãn (category/priority)
    - Lịch sử 7 ngày gần nhất (task tạo mới mỗi ngày)
    """
    from sqlalchemy import func, cast, Date
    from datetime import datetime, timedelta

    user_id = get_current_user(request)

    # ── 1. Task tổng hợp (Notes của chính user) ──────────────────────
    all_notes = db.execute(text("""
        SELECT status, COUNT(*) as cnt
        FROM notes
        WHERE user_id = :uid
        GROUP BY status
    """), {"uid": user_id}).mappings().all()

    status_map = {r["status"]: r["cnt"] for r in all_notes}
    total_tasks     = sum(status_map.values())
    # Tính hoàn thành: "done" + "approved" (Đã duyệt) đều được coi là xong
    done_tasks      = status_map.get("done", 0) + status_map.get("approved", 0)
    todo_tasks      = status_map.get("todo", 0)
    inprogress_tasks = status_map.get("in_progress", 0)

    # ── 2. Task đã GIAO ĐI (assignments where sender = user) ─────────
    sent_rows = db.execute(text("""
        SELECT status, COUNT(*) as cnt
        FROM task_assignments
        WHERE sender_id = :uid
        GROUP BY status
    """), {"uid": user_id}).mappings().all()

    sent_map       = {r["status"]: r["cnt"] for r in sent_rows}
    sent_pending   = sent_map.get("pending",  0)
    sent_accepted  = sent_map.get("accepted", 0)
    sent_rejected  = sent_map.get("rejected", 0)
    total_sent     = sum(sent_map.values())

    # ── 3. Task ĐƯỢC GIAO (assignments where receiver = user) ─────────
    recv_rows = db.execute(text("""
        SELECT status, COUNT(*) as cnt
        FROM task_assignments
        WHERE receiver_id = :uid
        GROUP BY status
    """), {"uid": user_id}).mappings().all()

    recv_map       = {r["status"]: r["cnt"] for r in recv_rows}
    recv_pending   = recv_map.get("pending",  0)
    recv_accepted  = recv_map.get("accepted", 0)
    recv_rejected  = recv_map.get("rejected", 0)
    total_received = sum(recv_map.values())

    # ── 4. Phân bổ theo mức độ ưu tiên ────────────────────────────────
    priority_rows = db.execute(text("""
        SELECT priority, COUNT(*) as cnt
        FROM notes
        WHERE user_id = :uid
        GROUP BY priority
        ORDER BY priority
    """), {"uid": user_id}).mappings().all()
    priority_data = [{"priority": r["priority"], "count": r["cnt"]} for r in priority_rows]

    # ── 5. Lịch sử 7 ngày (task tạo mới) ─────────────────────────────
    today = datetime.now().date()
    seven_days = db.execute(text("""
        SELECT DATE(created_at) as day, COUNT(*) as cnt
        FROM notes
        WHERE user_id = :uid
          AND created_at >= :start
        GROUP BY DATE(created_at)
        ORDER BY day
    """), {"uid": user_id, "start": today - timedelta(days=6)}).mappings().all()

    day_map = {str(r["day"]): r["cnt"] for r in seven_days}
    daily = []
    for i in range(7):
        d = today - timedelta(days=6 - i)
        daily.append({"date": str(d), "count": day_map.get(str(d), 0)})

    # ── 6. Tỉ lệ hoàn thành ───────────────────────────────────────────
    completion_rate = round((done_tasks / total_tasks * 100) if total_tasks else 0, 1)

    # ── 7. Task trễ hạn (overdue_list) ────────────────────────────────
    now_dt = datetime.now()
    overdue_rows = db.execute(text("""
        SELECT id, title, due_date, priority
        FROM notes
        WHERE user_id = :uid
          AND status != 'done'
          AND due_date < :now
        ORDER BY due_date ASC
        LIMIT 10
    """), {"uid": user_id, "now": now_dt}).mappings().all()

    overdue_list = [
        {
            "id":       r["id"],
            "title":    r["title"],
            "due_date": r["due_date"].isoformat() if r["due_date"] else None,
            "priority": r["priority"],
        }
        for r in overdue_rows
    ]
    overdue_tasks = len(overdue_list)

    # ── 8. Task tạo hôm nay (today_list) ──────────────────────────────
    today_start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end   = now_dt.replace(hour=23, minute=59, second=59, microsecond=999999)

    today_rows = db.execute(text("""
        SELECT id, title, created_at, priority
        FROM notes
        WHERE user_id = :uid
          AND status NOT IN ('done', 'approved')
          AND created_at >= :start
          AND created_at <= :end
        ORDER BY priority DESC, created_at ASC
        LIMIT 10
    """), {"uid": user_id, "start": today_start, "end": today_end}).mappings().all()

    today_list = [
        {
            "id":         r["id"],
            "title":      r["title"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "priority":   r["priority"],
        }
        for r in today_rows
    ]
    today_count = len(today_list)

    # ── 9. Hoạt động gần đây (recent_list) ────────────────────────────
    recent_rows = db.execute(text("""
        SELECT id, title, status, updated_at, created_at
        FROM notes
        WHERE user_id = :uid
        ORDER BY updated_at DESC
        LIMIT 6
    """), {"uid": user_id}).mappings().all()

    recent_list = []
    for r in recent_rows:
        if r["status"] == "done":
            action = "done"
        elif r["updated_at"] and r["created_at"] and r["updated_at"] != r["created_at"]:
            action = "updated"
        else:
            action = "created"
        recent_list.append({
            "id":     r["id"],
            "title":  r["title"],
            "action": action,
        })

    # ── 10. Việc cần làm ngay (focus_list) ────────────────────────────
    # Ưu tiên: (1) trễ hạn + ưu tiên cao, (2) hạn hôm nay, (3) ưu tiên cao chưa done
    focus_rows = db.execute(text("""
        SELECT id, title, due_date, priority, label, status
        FROM notes
        WHERE user_id = :uid
          AND status != 'done'
        ORDER BY
            CASE WHEN due_date < :now AND due_date IS NOT NULL THEN 0 ELSE 1 END,
            priority DESC,
            due_date ASC NULLS LAST
        LIMIT 5
    """), {"uid": user_id, "now": now_dt}).mappings().all()

    focus_list = []
    for r in focus_rows:
        reason_parts = []
        p = r["priority"] or 2
        p_labels = {1: "Ưu tiên thấp", 2: "Ưu tiên trung bình", 3: "Ưu tiên cao"}
        if r["due_date"] and r["due_date"] < now_dt:
            diff_days = (now_dt - r["due_date"]).days
            if diff_days > 0:
                reason_parts.append(f"Trễ hạn {diff_days} ngày")
            else:
                diff_h = int((now_dt - r["due_date"]).total_seconds() / 3600)
                reason_parts.append(f"Trễ hạn {diff_h} giờ")
        elif r["due_date"] and today_start <= r["due_date"] <= today_end:
            reason_parts.append("Hạn hôm nay")
        reason_parts.append(p_labels.get(p, ""))
        focus_list.append({
            "id":          r["id"],
            "title":       r["title"],
            "priority":    p,
            "label":       r["label"] or "",
            "action_type": r["label"] or "",
            "reason":      " + ".join(filter(None, reason_parts)),
        })

    return {
        # Task cá nhân
        "total_tasks":        total_tasks,
        "done_tasks":         done_tasks,
        "todo_tasks":         todo_tasks,
        "inprogress_tasks":   inprogress_tasks,
        "completion_rate":    completion_rate,
        # Thống kê thêm
        "overdue_tasks":      overdue_tasks,
        "today_count":        today_count,
        # Danh sách chi tiết cho home page
        "overdue_list":       overdue_list,
        "today_list":         today_list,
        "recent_list":        recent_list,
        "focus_list":         focus_list,
        # Giao đi
        "total_sent":         total_sent,
        "sent_pending":       sent_pending,
        "sent_accepted":      sent_accepted,
        "sent_rejected":      sent_rejected,
        # Nhận về
        "total_received":     total_received,
        "recv_pending":       recv_pending,
        "recv_accepted":      recv_accepted,
        "recv_rejected":      recv_rejected,
        # Phân bổ
        "priority_data":      priority_data,
        "daily":              daily,
    }