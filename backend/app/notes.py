from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Note
from datetime import date
from typing import Optional
from jose import JWTError, jwt

router = APIRouter()

SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_current_user(request: Request) -> int:
    """Lấy user_id từ JWT token trong header"""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Chưa đăng nhập")
    
    try:
        scheme, token = auth_header.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Header không hợp lệ")
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token không hợp lệ")
        return int(user_id)
    except JWTError:
        raise HTTPException(status_code=401, detail="Token không hợp lệ")
    except ValueError:
        raise HTTPException(status_code=401, detail="Header không hợp lệ")

@router.post("/notes")
def create_note(request: Request, title: str = Form(...), content: str = Form(""), status: str = Form("todo"), priority: int = Form(1), due_date: Optional[str] = Form(None), is_quick_add: bool = Form(False), db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    due = None
    if due_date:
        try:
            due = date.fromisoformat(due_date)
        except:
            pass
    note = Note(title=title, content=content, status=status, priority=priority, due_date=due, is_quick_add=is_quick_add, user_id=user_id)
    db.add(note)
    db.commit()
    db.refresh(note)
    return {"id": note.id, "title": note.title, "content": note.content, "status": note.status, "priority": note.priority, "due_date": note.due_date, "is_quick_add": note.is_quick_add}

@router.get("/notes")
def list_notes(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    notes = db.query(Note).filter(Note.user_id == user_id).order_by(Note.created_at.desc()).all()
    return [{"id": n.id, "title": n.title, "content": n.content, "status": n.status, "priority": n.priority, "due_date": n.due_date, "is_quick_add": n.is_quick_add, "created_at": n.created_at} for n in notes]

@router.get("/notes/{note_id}")
def get_note(note_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Ghi chú không tìm thấy")
    return {"id": note.id, "title": note.title, "content": note.content, "status": note.status, "priority": note.priority, "due_date": note.due_date, "is_quick_add": note.is_quick_add}

@router.put("/notes/{note_id}")
def update_note(note_id: int, request: Request, title: str = Form(...), content: str = Form(""), status: str = Form("todo"), priority: int = Form(1), due_date: Optional[str] = Form(None), db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Ghi chú không tìm thấy")
    note.title = title
    note.content = content
    note.status = status
    note.priority = priority
    if due_date:
        try:
            note.due_date = date.fromisoformat(due_date)
        except:
            note.due_date = None
    else:
        note.due_date = None
    db.commit()
    return {"id": note.id, "title": note.title, "content": note.content, "status": note.status, "priority": note.priority, "due_date": note.due_date}

@router.delete("/notes/{note_id}")
def delete_note(note_id: int, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user(request)
    note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Ghi chú không tìm thấy")
    db.delete(note)
    db.commit()
    return {"message": "Ghi chú đã xóa"}