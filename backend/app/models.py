from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, Boolean, Float
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())


# =====================================================================
# Project — dự án nhóm các task lại
# =====================================================================
class Project(Base):
    """
    Mỗi dự án thuộc về 1 user (owner).
    Task thuộc dự án qua Note.project_id.
    """
    __tablename__ = "projects"

    id          = Column(Integer, primary_key=True)
    owner_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    name        = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at  = Column(TIMESTAMP, server_default=func.now())


# =====================================================================
# ProjectMember — thành viên dự án (nhiều-nhiều)
# =====================================================================
class ProjectMember(Base):
    """
    Bảng trung gian: 1 user được thêm vào 1 project bởi owner.
    Owner không cần có entry ở đây — kiểm tra qua Project.owner_id.
    """
    __tablename__ = "project_members"

    id         = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id",    ondelete="CASCADE"), nullable=False)
    joined_at  = Column(TIMESTAMP, server_default=func.now())


class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)   # None = Công việc cá nhân
    title = Column(String)
    content = Column(Text)
    status = Column(String, default="todo")
    priority = Column(Integer, default=1)
    due_date = Column(TIMESTAMP, nullable=True)
    label = Column(String(100), nullable=True)
    is_quick_add = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())


class Suggestion(Base):
    __tablename__ = "suggestions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_text = Column(Text, nullable=False)
    action_type = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=True)
    title = Column(String(255), nullable=False)
    suggested_priority = Column(Integer, default=2)
    deadline = Column(TIMESTAMP, nullable=True)
    template_style = Column(String(50), nullable=True)
    template_subject = Column(Text, nullable=True)
    template_body = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False)
    edited_title = Column(String(255), nullable=True)
    edited_priority = Column(Integer, nullable=True)
    note_id = Column(Integer, ForeignKey("notes.id"), nullable=True)
    feedback_action = Column(String(20), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())


# =====================================================================
# MỚI: TaskAssignment — lưu việc giao task giữa 2 tài khoản
# Dùng cho nhãn "Giao việc" và "Lên lịch họp"
# =====================================================================
class TaskAssignment(Base):
    """
    Bảng lưu task được giao từ user này sang user khác.
    sender_id   = người giao việc / người tổ chức họp
    receiver_id = người nhận việc / người được mời họp
    status: pending → accepted / rejected
    """
    __tablename__ = "task_assignments"

    id          = Column(Integer, primary_key=True)
    note_id     = Column(Integer, ForeignKey("notes.id"), nullable=False)
    sender_id   = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # "task" = giao việc, "meeting" = lên lịch họp
    assignment_type = Column(String(20), default="task", nullable=False)

    # pending / accepted / rejected
    status      = Column(String(20), default="pending", nullable=False)

    # Tin nhắn kèm theo khi giao (tuỳ chọn)
    message     = Column(Text, nullable=True)

    created_at  = Column(TIMESTAMP, server_default=func.now())
    responded_at = Column(TIMESTAMP, nullable=True)


# =====================================================================
# MỚI: Notification — thông báo realtime trong app
# =====================================================================
class Notification(Base):
    """
    Thông báo hiển thị trong icon 🔔 trên header.
    type:
      - "task_assigned"   → được giao việc mới
      - "meeting_invited" → được mời họp
      - "task_accepted"   → người nhận đã chấp nhận task của bạn
      - "task_rejected"   → người nhận từ chối task của bạn
    """
    __tablename__ = "notifications"

    id              = Column(Integer, primary_key=True)
    user_id         = Column(Integer, ForeignKey("users.id"), nullable=False)
    sender_id       = Column(Integer, ForeignKey("users.id"), nullable=True)
    type            = Column(String(50), nullable=False)
    title           = Column(String(255), nullable=False)
    body            = Column(Text, nullable=True)
    assignment_id   = Column(Integer, ForeignKey("task_assignments.id"), nullable=True)
    note_id         = Column(Integer, ForeignKey("notes.id"), nullable=True)
    is_read         = Column(Boolean, default=False)
    created_at      = Column(TIMESTAMP, server_default=func.now())