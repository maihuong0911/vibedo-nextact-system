from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Note
from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from .dependencies import get_current_user

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Schema PATCH (JSON) — giữ nguyên ────────────────────────────────────
class NotePatch(BaseModel):
    status:     Optional[str] = None
    priority:   Optional[int] = None
    title:      Optional[str] = None
    content:    Optional[str] = None
    due_date:   Optional[str] = None
    label:      Optional[str] = None
    project_id: Optional[int] = None


# ── Helper: đọc body dù là JSON hay FormData ────────────────────────────
async def _parse_body(request: Request) -> dict:
    """Tự động nhận biết Content-Type và parse tương ứng."""
    ct = request.headers.get("content-type", "")
    if "application/json" in ct:
        try:
            return await request.json()
        except Exception:
            return {}
    else:
        try:
            form = await request.form()
            return dict(form)
        except Exception:
            return {}


# ── Helper: parse due_date an toàn ──────────────────────────────────────
def _parse_due_date(value) -> Optional[datetime]:
    if not value or str(value).strip() in ("", "null", "None", "undefined"):
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except (ValueError, TypeError):
        return None


# ── Helper: parse int an toàn ───────────────────────────────────────────
def _int(value, default=None) -> Optional[int]:
    if value is None or str(value).strip() in ("", "null", "None"):
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# ════════════════════════════════════════════════════════════════════════
# GET /notes  — Lấy danh sách ghi chú
# ════════════════════════════════════════════════════════════════════════
@router.get("")
def get_notes(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    notes = (
        db.query(Note)
        .filter(Note.user_id == user_id)
        .order_by(Note.created_at.desc())
        .all()
    )
    return notes


# ════════════════════════════════════════════════════════════════════════
# POST /notes — Tạo ghi chú mới (nhận JSON hoặc FormData)
# ════════════════════════════════════════════════════════════════════════
@router.post("")
async def create_note(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    data = await _parse_body(request)

    title = str(data.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=422, detail="Tiêu đề không được để trống")

    priority   = _int(data.get("priority"), 2)
    project_id = _int(data.get("project_id"))
    if project_id is not None and project_id <= 0:
        project_id = None

    new_note = Note(
        user_id    = user_id,
        title      = title,
        content    = data.get("content") or None,
        status     = str(data.get("status") or "todo"),
        priority   = priority,
        label      = data.get("label") or None,
        project_id = project_id,
        due_date   = _parse_due_date(data.get("due_date")),
    )

    # is_quick_add (tuỳ model có hay không)
    if hasattr(new_note, "is_quick_add"):
        iq = data.get("is_quick_add", False)
        new_note.is_quick_add = iq if isinstance(iq, bool) else str(iq).lower() in ("1", "true")

    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note


# ════════════════════════════════════════════════════════════════════════
# PUT /notes/{note_id} — Cập nhật toàn bộ (nhận JSON hoặc FormData)
# ════════════════════════════════════════════════════════════════════════
@router.put("/{note_id}")
async def update_note(note_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Ghi chú không tìm thấy")

    data = await _parse_body(request)

    title = str(data.get("title") or "").strip()
    if title:
        note.title = title

    # content — cho phép xóa trắng (truyền "" → None)
    if "content" in data:
        note.content = data["content"] or None

    if data.get("status"):
        note.status = str(data["status"])

    priority = _int(data.get("priority"))
    if priority is not None:
        note.priority = priority

    if "label" in data:
        note.label = data["label"] or None

    # project_id — 0 hoặc "" → trả về cá nhân
    if "project_id" in data:
        pid = _int(data.get("project_id"))
        if pid is not None:
            note.project_id = pid if pid > 0 else None

    # due_date — "" / null → xoá hạn chót
    if "due_date" in data:
        note.due_date = _parse_due_date(data.get("due_date"))

    db.commit()
    db.refresh(note)
    return note


# ════════════════════════════════════════════════════════════════════════
# PATCH /notes/{note_id} — Cập nhật một phần (JSON body qua Pydantic)
# ════════════════════════════════════════════════════════════════════════
@router.patch("/{note_id}")
def patch_note(
    note_id: int,
    request: Request,
    payload: NotePatch,
    db: Session = Depends(get_db),
):
    user_id = get_current_user(request)
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Ghi chú không tìm thấy")

    if payload.status   is not None: note.status   = payload.status
    if payload.priority is not None: note.priority = payload.priority
    if payload.title    is not None: note.title    = payload.title
    if payload.content  is not None: note.content  = payload.content
    if payload.label    is not None: note.label    = payload.label
    if payload.project_id is not None:
        note.project_id = payload.project_id if payload.project_id > 0 else None

    if payload.due_date is not None:
        if payload.due_date.strip() in ("", "null"):
            note.due_date = None
        else:
            try:
                note.due_date = datetime.fromisoformat(payload.due_date.replace("Z", ""))
            except ValueError:
                pass

    db.commit()
    db.refresh(note)
    return note


# ════════════════════════════════════════════════════════════════════════
# DELETE /notes/{note_id}
# ════════════════════════════════════════════════════════════════════════
@router.delete("/{note_id}")
def delete_note(note_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Ghi chú không tìm thấy")
    db.delete(note)
    db.commit()
    return {"message": "Ghi chú đã xóa"}