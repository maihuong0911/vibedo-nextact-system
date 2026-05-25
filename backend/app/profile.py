"""
profile.py — API quản lý thông tin cá nhân
  GET  /me          → lấy thông tin user hiện tại
  PUT  /me          → cập nhật thông tin (full_name, gender, birthday, bio)
  POST /me/avatar   → upload ảnh đại diện (multipart/form-data)
  DELETE /me/avatar → xóa ảnh đại diện

⚠️  Dùng raw SQL cho gender/birthday/bio/avatar_url vì các cột này được
    thêm bằng ALTER TABLE sau khi User model đã định nghĩa — SQLAlchemy
    ORM không tự map column mới nếu không khai báo trong class.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import uuid
from pathlib import Path

from .database import SessionLocal
from .dependencies import get_current_user

router = APIRouter(prefix="/me", tags=["profile"])

# Thư mục lưu avatar
AVATAR_DIR  = Path(__file__).parent.parent.parent / "frontend" / "static" / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_SIZE_MB  = 5

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── Lấy user row bằng raw SQL (đọc được cả cột mới ALTER TABLE) ───────
def _fetch_user_raw(db: Session, user_id: int) -> dict | None:
    row = db.execute(
        text("""
            SELECT id, full_name, email,
                   avatar_url, gender,
                   birthday::text,
                   bio, created_at
            FROM users WHERE id = :uid
        """),
        {"uid": user_id}
    ).mappings().first()
    return dict(row) if row else None

def _user_dict(row: dict) -> dict:
    created = row.get("created_at")
    return {
        "id":         row["id"],
        "full_name":  row["full_name"],
        "email":      row["email"],
        "gender":     row.get("gender"),
        "birthday":   row.get("birthday"),
        "bio":        row.get("bio"),
        "avatar_url": row.get("avatar_url"),
        "created_at": created.isoformat() if hasattr(created, "isoformat") else str(created) if created else None,
    }

# ── GET /me ───────────────────────────────────────────────────────────
@router.get("")
def get_profile(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    row = _fetch_user_raw(db, user_id)
    if not row:
        raise HTTPException(404, "Khong tim thay nguoi dung")
    return _user_dict(row)

# ── PUT /me ───────────────────────────────────────────────────────────
class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    gender:    Optional[str] = None   # "male" | "female" | "other" | ""
    birthday:  Optional[str] = None   # "YYYY-MM-DD" | ""
    bio:       Optional[str] = None

@router.put("")
def update_profile(payload: ProfileUpdate, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    row = _fetch_user_raw(db, user_id)
    if not row:
        raise HTTPException(404, "Khong tim thay nguoi dung")

    # Validate full_name
    if payload.full_name is not None:
        name = payload.full_name.strip()
        if not name:
            raise HTTPException(400, "Ho ten khong duoc de trong")
    else:
        name = row["full_name"]

    # Merge: nếu frontend không gửi field → giữ nguyên giá trị cũ
    gender   = payload.gender   if payload.gender   is not None else row.get("gender")
    birthday = payload.birthday if payload.birthday is not None else row.get("birthday")
    bio      = payload.bio      if payload.bio      is not None else row.get("bio")

    # Chuẩn hoá: chuỗi rỗng → NULL
    gender   = gender   if gender   else None
    birthday = birthday if birthday else None
    bio      = bio      if bio      else None

    # Raw SQL UPDATE — đảm bảo lưu dù model ORM không khai báo column
    db.execute(
        text("""
            UPDATE users
            SET full_name = :full_name,
                gender    = :gender,
                birthday  = :birthday,
                bio       = :bio
            WHERE id = :uid
        """),
        {
            "full_name": name,
            "gender":    gender,
            "birthday":  birthday,
            "bio":       bio,
            "uid":       user_id,
        }
    )
    db.commit()

    updated = _fetch_user_raw(db, user_id)
    return _user_dict(updated)

# ── POST /me/avatar ───────────────────────────────────────────────────
@router.post("/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    user_id = get_current_user(request)
    row = _fetch_user_raw(db, user_id)
    if not row:
        raise HTTPException(404, "Khong tim thay nguoi dung")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Chi chap nhan {', '.join(ALLOWED_EXTS)}")

    content = await file.read()
    if len(content) > MAX_SIZE_MB * 1024 * 1024:
        raise HTTPException(400, f"Anh toi da {MAX_SIZE_MB}MB")

    # Xóa avatar cũ
    old_url = row.get("avatar_url")
    if old_url and old_url.startswith("/static/avatars/"):
        old_path = AVATAR_DIR / old_url.split("/")[-1]
        if old_path.exists():
            old_path.unlink(missing_ok=True)

    # Lưu file mới
    filename  = f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = AVATAR_DIR / filename
    with open(save_path, "wb") as f:
        f.write(content)

    new_url = f"/static/avatars/{filename}"

    db.execute(
        text("UPDATE users SET avatar_url = :url WHERE id = :uid"),
        {"url": new_url, "uid": user_id}
    )
    db.commit()

    return {"avatar_url": new_url}

# ── DELETE /me/avatar ─────────────────────────────────────────────────
@router.delete("/avatar")
def delete_avatar(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    row = _fetch_user_raw(db, user_id)
    if not row:
        raise HTTPException(404, "Khong tim thay nguoi dung")

    old_url = row.get("avatar_url")
    if old_url and old_url.startswith("/static/avatars/"):
        old_path = AVATAR_DIR / old_url.split("/")[-1]
        if old_path.exists():
            old_path.unlink(missing_ok=True)

    db.execute(
        text("UPDATE users SET avatar_url = NULL WHERE id = :uid"),
        {"uid": user_id}
    )
    db.commit()
    return {"success": True}