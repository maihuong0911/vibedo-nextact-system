"""
home.py - Dashboard AI Focus routes
Cung cấp dữ liệu cho trang chủ từ DB thật
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Note, Suggestion, TaskAssignment
from datetime import date, datetime
from .dependencies import get_current_user


def to_date(value) -> date:
    """
    Chuyển an toàn sang datetime.date — xử lý cả hai trường hợp:
    - datetime.datetime  → gọi .date()
    - datetime.date      → trả về nguyên
    """
    if isinstance(value, datetime):
        return value.date()
    return value  # đã là date

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/api/home")
def get_home_data(request: Request, db: Session = Depends(get_db)):
    """
    Lấy dữ liệu dashboard cho trang chủ — DỮ LIỆU THẬT từ DB.

    Response:
    {
        "ai_focus": [...],              # 3 task được AI đề xuất ưu tiên cao
        "today_count": 5,               # Số task có deadline hôm nay
        "overdue_count": 2,             # Số task trễ hạn
        "pending_suggestions_count": 1, # Số gợi ý chưa duyệt (từ bảng suggestions thật)
        "completion_rate": 68,          # Phần trăm hoàn thành
        "action_types": {...}           # Distribution loại hành động
    }
    """
    user_id = get_current_user(request)
    today = date.today()

    # Lấy tất cả notes của user
    all_notes = db.query(Note).filter(Note.user_id == user_id).all()

    # === AI FOCUS: 3 task ưu tiên cao nhất ===
    # Lọc các task chưa done, sắp xếp: priority cao → due_date sắp tới → created_at mới
    active_notes = [n for n in all_notes if n.status not in ('done', 'approved')]

    sorted_notes = sorted(
        active_notes,
        key=lambda n: (
            -n.priority,
            (to_date(n.due_date) - today).days if n.due_date and to_date(n.due_date) >= today else 999,
            -n.created_at.timestamp() if n.created_at else 0
        )
    )

    ai_focus = []
    for note in sorted_notes[:3]:
        action_type = _infer_action_type(note.title, note.label)
        reason = _generate_reason(note.priority, note.due_date, today)

        ai_focus.append({
            "id": note.id,
            "title": note.title,
            "action_type": action_type,
            "deadline": note.due_date.isoformat() if note.due_date else None,
            "priority": note.priority,
            "reason": reason
        })

    # === TODAY TASKS — so sánh đúng kiểu date ===
    today_count = sum(
        1 for n in all_notes
        if n.due_date and to_date(n.due_date) == today
    )

    # === OVERDUE TASKS ===
    overdue_count = sum(
        1 for n in all_notes
        if n.due_date and to_date(n.due_date) < today and n.status not in ('done', 'approved')
    )

    # === PENDING SUGGESTIONS — lấy từ bảng suggestions thật ===
    try:
        pending_suggestions_count = db.query(Suggestion).filter(
            Suggestion.user_id == user_id,
            Suggestion.status == 'pending'
        ).count()
    except Exception:
        # Fallback nếu bảng chưa migrate
        pending_suggestions_count = 0

    # === COMPLETION RATE ===
    completed = sum(1 for n in all_notes if n.status in ('done', 'approved'))
    total = len(all_notes)
    completion_rate = round((completed / total * 100) if total > 0 else 0)

    # === ACTION TYPES DISTRIBUTION — dùng label từ AI nếu có ===
    action_types_full = {}
    for note in all_notes:
        action_type = _infer_action_type(note.title, note.label)
        action_types_full[action_type] = action_types_full.get(action_type, 0) + 1

    return {
        "ai_focus": ai_focus,
        "today_count": today_count,
        "overdue_count": overdue_count,
        "pending_suggestions_count": pending_suggestions_count,
        "completion_rate": completion_rate,
        "action_types": action_types_full
    }


# =====================================================================
# GET /stats — Dữ liệu đầy đủ cho trang Tổng quan (home.html)
# =====================================================================
@router.get("/stats")
def get_stats(request: Request, db: Session = Depends(get_db)):
    """
    Trả về toàn bộ số liệu cho trang chủ:
    - Tổng task, hoàn thành, đang làm, trễ hạn
    - Biểu đồ 7 ngày
    - Phân bổ ưu tiên
    - Giao việc (đã giao / được giao)
    - Danh sách việc trễ hạn chi tiết
    """
    user_id = get_current_user(request)
    today   = datetime.now()
    today_d = today.date()

    all_notes = db.query(Note).filter(Note.user_id == user_id).all()

    # ── Tổng quan ──────────────────────────────────────────────────
    total_tasks     = len(all_notes)
    # "done" + "approved" (Đã duyệt) đều tính là hoàn thành
    done_tasks      = sum(1 for n in all_notes if n.status in ('done', 'approved'))
    inprogress_tasks = sum(1 for n in all_notes if n.status == 'in_progress')  # fix: có underscore
    todo_tasks      = sum(1 for n in all_notes if n.status == 'todo')
    completion_rate = round(done_tasks / total_tasks * 100) if total_tasks else 0

    # ── Trễ hạn ────────────────────────────────────────────────────
    overdue_notes = [
        n for n in all_notes
        if n.due_date and to_date(n.due_date) < today_d and n.status not in ('done', 'approved')
    ]
    overdue_notes.sort(key=lambda n: to_date(n.due_date))  # cũ nhất trước
    overdue_tasks = len(overdue_notes)
    overdue_list  = [
        {
            "id":       n.id,
            "title":    n.title,
            "due_date": n.due_date.isoformat() if n.due_date else None,
            "priority": n.priority,
            "status":   n.status,
        }
        for n in overdue_notes[:10]
    ]

    # ── 7 ngày gần nhất ───────────────────────────────────────────
    from datetime import timedelta
    daily = []
    for i in range(6, -1, -1):
        d = today_d - timedelta(days=i)
        count = sum(
            1 for n in all_notes
            if n.created_at and to_date(n.created_at) == d
        )
        daily.append({"date": d.isoformat(), "count": count})

    # ── Phân bổ ưu tiên ───────────────────────────────────────────
    from collections import Counter
    prio_counter = Counter(n.priority for n in all_notes if n.priority)
    priority_data = [{"priority": k, "count": v} for k, v in sorted(prio_counter.items())]

    # ── Giao việc ─────────────────────────────────────────────────
    try:
        sent_all = db.query(TaskAssignment).filter(
            TaskAssignment.sender_id == user_id
        ).all()
        recv_all = db.query(TaskAssignment).filter(
            TaskAssignment.receiver_id == user_id
        ).all()

        total_sent     = len(sent_all)
        sent_pending   = sum(1 for a in sent_all if a.status == 'pending')
        sent_accepted  = sum(1 for a in sent_all if a.status == 'accepted')
        sent_rejected  = sum(1 for a in sent_all if a.status == 'rejected')

        total_received = len(recv_all)
        recv_pending   = sum(1 for a in recv_all if a.status == 'pending')
        recv_accepted  = sum(1 for a in recv_all if a.status == 'accepted')
        recv_rejected  = sum(1 for a in recv_all if a.status == 'rejected')
    except Exception:
        total_sent = sent_pending = sent_accepted = sent_rejected = 0
        total_received = recv_pending = recv_accepted = recv_rejected = 0

    # ── Việc cần làm ngay (focus_list) ───────────────────────────
    active = [n for n in all_notes if n.status not in ('done', 'approved')]
    active_sorted = sorted(
        active,
        key=lambda n: (
            -n.priority,
            (to_date(n.due_date) - today_d).days if n.due_date and to_date(n.due_date) >= today_d else 0,
            -(n.created_at.timestamp() if n.created_at else 0)
        )
    )
    focus_list = [
        {
            "id":          n.id,
            "title":       n.title,
            "priority":    n.priority,
            "label":       n.label or _infer_action_type(n.title, n.label),
            "action_type": _infer_action_type(n.title, n.label),
            "reason":      _generate_reason(n.priority, n.due_date, today_d),
            "due_date":    n.due_date.isoformat() if n.due_date else None,
        }
        for n in active_sorted[:5]
    ]

    # ── Task tạo hôm nay (today_list) ────────────────────────────────
    today_list = [
        {
            "id":       n.id,
            "title":    n.title,
            "priority": n.priority,
        }
        for n in all_notes
        if n.created_at and to_date(n.created_at) == today_d and n.status not in ('done', 'approved')
    ]

    # ── Gần đây (recent_list) — 6 task mới nhất ───────────────────
    recent_sorted = sorted(
        all_notes,
        key=lambda n: n.created_at.timestamp() if n.created_at else 0,
        reverse=True
    )
    recent_list = [
        {
            "id":     n.id,
            "title":  n.title,
            "action": "done" if n.status in ("done", "approved") else "created",
        }
        for n in recent_sorted[:6]
    ]

    return {
        # Tổng quan
        "total_tasks":      total_tasks,
        "done_tasks":       done_tasks,
        "inprogress_tasks": inprogress_tasks,
        "todo_tasks":       todo_tasks,
        "completion_rate":  completion_rate,
        # Trễ hạn
        "overdue_tasks":    overdue_tasks,
        "overdue_list":     overdue_list,
        # Hôm nay
        "today_count":      len(today_list),
        "today_list":       today_list,
        # Focus
        "focus_list":       focus_list,
        # Gần đây
        "recent_list":      recent_list,
        # 7 ngày
        "daily":            daily,
        # Ưu tiên
        "priority_data":    priority_data,
        # Giao việc
        "total_sent":       total_sent,
        "sent_pending":     sent_pending,
        "sent_accepted":    sent_accepted,
        "sent_rejected":    sent_rejected,
        "total_received":   total_received,
        "recv_pending":     recv_pending,
        "recv_accepted":    recv_accepted,
        "recv_rejected":    recv_rejected,
    }


def _infer_action_type(title: str, label: str = None) -> str:
    """
    Ưu tiên dùng label từ PhoBERT (đã lưu trong DB).
    Fallback về keyword matching nếu label rỗng.
    Bộ 6 nhãn: Lên lịch họp, Gửi/Trả lời email, Soạn báo cáo, Giao việc, Tạo nhắc nhở, Phê duyệt
    """
    VALID = {'Lên lịch họp', 'Gửi/Trả lời email', 'Soạn báo cáo',
             'Giao việc', 'Tạo nhắc nhở', 'Phê duyệt'}

    # Ưu tiên label AI đã phân loại
    if label and label.strip() in VALID:
        return label

    # Fallback: keyword matching cho 6 nhãn mới
    title_lower = title.lower()
    if any(w in title_lower for w in ['hẹn', 'lịch', 'cuộc họp', 'meeting', 'call', 'họp']):
        return 'Lên lịch họp'
    elif any(w in title_lower for w in ['gửi', 'email', 'mail', 'tin nhắn', 'trả lời', 'rep ', 'fwd']):
        return 'Gửi/Trả lời email'
    elif any(w in title_lower for w in ['báo cáo', 'report', 'soạn', 'viết', 'draft', 'tài liệu']):
        return 'Soạn báo cáo'
    elif any(w in title_lower for w in ['duyệt', 'approve', 'phê duyệt', 'ký', 'xác nhận', 'sign']):
        return 'Phê duyệt'
    elif any(w in title_lower for w in ['nhắc', 'reminder', 'nhớ', 'đừng quên', 'deadline']):
        return 'Tạo nhắc nhở'
    elif any(w in title_lower for w in ['giao', 'assign', 'phân công', 'theo dõi', 'check', 'follow']):
        return 'Giao việc'
    else:
        return 'Giao việc'  # fallback mặc định — tổng quát nhất


def _generate_reason(priority: int, due_date, today: date) -> str:
    """Tạo lý do gợi ý từ AI"""
    reasons = []

    if priority == 3:
        reasons.append("Ưu tiên cao")
    elif priority == 2:
        reasons.append("Ưu tiên trung bình")

    if due_date:
        due_day = to_date(due_date)
        days_left = (due_day - today).days
        if days_left == 0:
            reasons.append("Hạn chót hôm nay")
        elif days_left == 1:
            reasons.append("Hạn chót ngày mai")
        elif 0 < days_left <= 3:
            reasons.append(f"Hạn chót trong {days_left} ngày")
        elif days_left < 0:
            reasons.append(f"Trễ hạn {abs(days_left)} ngày")

    if not reasons:
        reasons.append("Được đề xuất dựa trên mô hình AI")

    return " + ".join(reasons)