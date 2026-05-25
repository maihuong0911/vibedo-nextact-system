"""
projects.py — API endpoints cho Dự án + Thành viên dự án.
Dùng raw SQL thay vì ORM để tránh lỗi ImportError khi models.py
không khai báo đủ các class (Project, ProjectMember, Notification...).

Router prefix="/projects"
users_router prefix="/users"  — include riêng trong main.py.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional, List

from .database import SessionLocal
from .dependencies import get_current_user

router       = APIRouter(prefix="/projects", tags=["projects"])
users_router = APIRouter(prefix="/users",    tags=["users"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Pydantic schemas ──────────────────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    member_ids: Optional[List[int]] = []

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class AddMemberPayload(BaseModel):
    user_id: int


# ── Helpers ───────────────────────────────────────────────────────────
def _row_to_proj(row: dict, task_count: int = 0) -> dict:
    created = row.get("created_at")
    return {
        "id":          row["id"],
        "name":        row["name"],
        "description": row.get("description") or "",
        "owner_id":    row["owner_id"],
        "task_count":  task_count,
        "created_at":  created.isoformat() if hasattr(created, "isoformat") else str(created) if created else None,
    }

def _get_project(db: Session, project_id: int) -> dict | None:
    row = db.execute(
        text("SELECT id, name, description, owner_id, created_at FROM projects WHERE id = :pid"),
        {"pid": project_id}
    ).mappings().first()
    return dict(row) if row else None

def _is_member(db: Session, project_id: int, user_id: int) -> bool:
    row = db.execute(
        text("SELECT 1 FROM project_members WHERE project_id=:pid AND user_id=:uid"),
        {"pid": project_id, "uid": user_id}
    ).first()
    return row is not None

def _check_accessible(db: Session, project_id: int, user_id: int) -> dict:
    proj = _get_project(db, project_id)
    if not proj:
        raise HTTPException(404, "Không tìm thấy dự án")
    if proj["owner_id"] != user_id and not _is_member(db, project_id, user_id):
        raise HTTPException(403, "Bạn không có quyền truy cập dự án này")
    return proj

def _task_count(db: Session, project_id: int) -> int:
    row = db.execute(
        text("SELECT COUNT(*) AS cnt FROM notes WHERE project_id = :pid"),
        {"pid": project_id}
    ).first()
    return row.cnt if row else 0

def _send_invite_notif(db: Session, sender_id: int, sender_name: str,
                       receiver_id: int, project_name: str, project_id: int):
    db.execute(text("""
        INSERT INTO notifications (user_id, sender_id, type, title, body, is_read)
        VALUES (:uid, :sid, 'project_added', :title, :body, false)
    """), {
        "uid":   receiver_id,
        "sid":   sender_id,
        "title": f'Bạn được thêm vào dự án "{project_name}"',
        "body":  f"do {sender_name} tạo",
    })


# ═══════════════════════════════════════════════════════════════════
# PROJECT CRUD
# ═══════════════════════════════════════════════════════════════════

@router.get("")
def list_projects(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)

    # Dự án sở hữu + dự án là thành viên
    rows = db.execute(text("""
        SELECT DISTINCT p.id, p.name, p.description, p.owner_id, p.created_at
        FROM projects p
        LEFT JOIN project_members pm ON pm.project_id = p.id
        WHERE p.owner_id = :uid OR pm.user_id = :uid
        ORDER BY p.created_at DESC
    """), {"uid": user_id}).mappings().all()

    result = []
    for r in rows:
        r = dict(r)
        result.append(_row_to_proj(r, _task_count(db, r["id"])))
    return result


@router.post("")
def create_project(payload: ProjectCreate, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(400, "Tên dự án không được trống")

    # Insert project
    row = db.execute(text("""
        INSERT INTO projects (owner_id, name, description, created_at)
        VALUES (:uid, :name, :desc, NOW())
        RETURNING id, name, description, owner_id, created_at
    """), {
        "uid":  user_id,
        "name": name,
        "desc": payload.description or "",
    }).mappings().first()
    proj = dict(row)
    project_id = proj["id"]

    # Lấy tên người tạo để gửi thông báo
    sender_row = db.execute(
        text("SELECT full_name FROM users WHERE id = :uid"),
        {"uid": user_id}
    ).first()
    sender_name = sender_row.full_name if sender_row else "Ai đó"

    # Thêm thành viên + gửi thông báo
    for mid in (payload.member_ids or []):
        if mid == user_id:
            continue
        exists = db.execute(
            text("SELECT 1 FROM users WHERE id = :uid"),
            {"uid": mid}
        ).first()
        if not exists:
            continue
        already = db.execute(
            text("SELECT 1 FROM project_members WHERE project_id=:pid AND user_id=:uid"),
            {"pid": project_id, "uid": mid}
        ).first()
        if not already:
            db.execute(
                text("INSERT INTO project_members (project_id, user_id) VALUES (:pid, :uid)"),
                {"pid": project_id, "uid": mid}
            )
            _send_invite_notif(db, user_id, sender_name, mid, name, project_id)

    db.commit()
    return _row_to_proj(proj, 0)


@router.get("/{project_id}")
def get_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    proj = _check_accessible(db, project_id, user_id)
    return _row_to_proj(proj, _task_count(db, project_id))


@router.put("/{project_id}")
def update_project(project_id: int, payload: ProjectUpdate,
                   request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    proj = _get_project(db, project_id)
    if not proj or proj["owner_id"] != user_id:
        raise HTTPException(404, "Không tìm thấy dự án")

    new_name = payload.name.strip() if payload.name is not None else proj["name"]
    new_desc = payload.description if payload.description is not None else proj.get("description", "")

    db.execute(text("""
        UPDATE projects SET name=:name, description=:desc WHERE id=:pid
    """), {"name": new_name, "desc": new_desc, "pid": project_id})
    db.commit()

    updated = _get_project(db, project_id)
    return _row_to_proj(updated, _task_count(db, project_id))


@router.delete("/{project_id}")
def delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    proj = _get_project(db, project_id)
    if not proj or proj["owner_id"] != user_id:
        raise HTTPException(404, "Không tìm thấy dự án")

    db.execute(text("UPDATE notes SET project_id=NULL WHERE project_id=:pid"), {"pid": project_id})
    db.execute(text("DELETE FROM project_members WHERE project_id=:pid"),      {"pid": project_id})
    db.execute(text("DELETE FROM projects WHERE id=:pid"),                      {"pid": project_id})
    db.commit()
    return {"success": True, "message": "Đã xóa dự án. Các task đã chuyển về Công việc cá nhân."}


# ═══════════════════════════════════════════════════════════════════
# PROJECT NOTES
# ═══════════════════════════════════════════════════════════════════

@router.get("/{project_id}/notes")
def get_project_notes(project_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    _check_accessible(db, project_id, user_id)

    notes = db.execute(text("""
        SELECT n.*, u.full_name AS creator_name
        FROM notes n
        LEFT JOIN users u ON u.id = n.user_id
        WHERE n.project_id = :pid
        ORDER BY n.created_at DESC
    """), {"pid": project_id}).mappings().all()

    result = []
    for n in notes:
        d = dict(n)
        # Serialize datetime fields
        for k, v in d.items():
            if hasattr(v, "isoformat"):
                d[k] = v.isoformat()
        result.append(d)
    return result


# ═══════════════════════════════════════════════════════════════════
# PROJECT MEMBERS
# ═══════════════════════════════════════════════════════════════════

@router.get("/{project_id}/members")
def get_project_members(project_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    proj = _check_accessible(db, project_id, user_id)
    owner_id = proj["owner_id"]

    rows = db.execute(text("""
        SELECT u.id, u.full_name, u.email
        FROM users u
        WHERE u.id = :owner_id
        UNION
        SELECT u.id, u.full_name, u.email
        FROM users u
        JOIN project_members pm ON pm.user_id = u.id
        WHERE pm.project_id = :pid AND u.id != :owner_id
    """), {"owner_id": owner_id, "pid": project_id}).mappings().all()

    result = []
    for r in rows:
        r = dict(r)
        result.append({
            "id":        r["id"],
            "full_name": r["full_name"],
            "email":     r["email"],
            "is_owner":  r["id"] == owner_id,
        })
    # Owner luôn đứng đầu
    result.sort(key=lambda x: (0 if x["is_owner"] else 1))
    return result


@router.post("/{project_id}/members")
def add_project_member(project_id: int, payload: AddMemberPayload,
                       request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    proj = _get_project(db, project_id)
    if not proj or proj["owner_id"] != user_id:
        raise HTTPException(403, "Chỉ chủ dự án mới có thể thêm thành viên")

    target = db.execute(
        text("SELECT id, full_name FROM users WHERE id = :uid"),
        {"uid": payload.user_id}
    ).first()
    if not target:
        raise HTTPException(404, "Không tìm thấy người dùng")

    if _is_member(db, project_id, payload.user_id):
        raise HTTPException(400, "Người dùng đã là thành viên")

    db.execute(
        text("INSERT INTO project_members (project_id, user_id) VALUES (:pid, :uid)"),
        {"pid": project_id, "uid": payload.user_id}
    )

    sender = db.execute(
        text("SELECT full_name FROM users WHERE id=:uid"), {"uid": user_id}
    ).first()
    sender_name = sender.full_name if sender else "Ai đó"
    _send_invite_notif(db, user_id, sender_name, payload.user_id, proj["name"], project_id)

    db.commit()
    return {"success": True, "message": f"Đã thêm {target.full_name} vào dự án"}


@router.delete("/{project_id}/members/{member_user_id}")
def remove_project_member(project_id: int, member_user_id: int,
                          request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    proj = _get_project(db, project_id)
    if not proj or proj["owner_id"] != user_id:
        raise HTTPException(403, "Chỉ chủ dự án mới có thể xóa thành viên")

    result = db.execute(
        text("DELETE FROM project_members WHERE project_id=:pid AND user_id=:uid"),
        {"pid": project_id, "uid": member_user_id}
    )
    if result.rowcount == 0:
        raise HTTPException(404, "Không tìm thấy thành viên")

    db.commit()
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════
# USER SEARCH  — prefix="/users" (users_router)
# ═══════════════════════════════════════════════════════════════════

@users_router.get("/search")
def search_users(q: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    q = q.strip()
    if len(q) < 2:
        return []
    pat = f"%{q}%"
    rows = db.execute(text("""
        SELECT id, full_name, email FROM users
        WHERE (full_name ILIKE :pat OR email ILIKE :pat)
          AND id != :uid
        LIMIT 10
    """), {"pat": pat, "uid": user_id}).mappings().all()
    return [{"id": r["id"], "full_name": r["full_name"], "email": r["email"]} for r in rows]