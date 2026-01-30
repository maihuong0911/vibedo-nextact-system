from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from .database import SessionLocal
from .models import User
from datetime import datetime, timedelta
from jose import JWTError, jwt
import json

router = APIRouter()
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# Secret key để ký JWT token
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_access_token(user_id: int):
    """Tạo JWT token"""
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {"sub": str(user_id), "exp": expire}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token

@router.post("/register")
def register(full_name: str = Form(...), email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    # Kiểm tra email đã tồn tại
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email đã tồn tại")
    
    hashed = pwd_context.hash(password)
    user = User(full_name=full_name, email=email, password_hash=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    
    token = create_access_token(user.id)
    return {"message": "Đăng ký thành công", "user_id": user.id, "token": token}

@router.post("/login")
def login(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not pwd_context.verify(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")
    
    token = create_access_token(user.id)
    return {"message": "Đăng nhập thành công", "user_id": user.id, "token": token, "full_name": user.full_name}