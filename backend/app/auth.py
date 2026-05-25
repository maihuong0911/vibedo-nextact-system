from fastapi import APIRouter, Depends, HTTPException, status, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import User
from .dependencies import (
    get_password_hash,
    verify_password,
    create_access_token
)

router = APIRouter(tags=["auth"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/login")
def login(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    print(f"📥 Login attempt: {email}")
    user = db.query(User).filter(User.email == email).first()

    if not user or not verify_password(password, user.password_hash):
        print(f"❌ Login failed for: {email}")
        # Nếu lỗi, quay lại trang login kèm thông báo (optional)
        raise HTTPException(status_code=401, detail="Email hoặc mật khẩu không đúng")

    # 1. Tạo Token
    access_token = create_access_token(data={"sub": str(user.id)})

    # 2. Tạo phản hồi Chuyển hướng (Redirect)
    # Bạn có thể đổi "/notes" thành "/dashboard" tùy theo app của bạn
    response = RedirectResponse(url="/home", status_code=status.HTTP_303_SEE_OTHER)

    # 3. Lưu Token vào Cookie
    # httponly=True giúp ngăn chặn script độc hại lấy token
    response.set_cookie(
        key="access_token", 
        value=f"Bearer {access_token}", 
        httponly=True,
        max_age=36000 # Thời gian sống của cookie (giây)
    )

    print(f" Login success & Cookie set for: {email}")
    return response

@router.post("/register")
def register(
    full_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email đã tồn tại")

    new_user = User(
        full_name=full_name,
        email=email,
        password_hash=get_password_hash(password)
    )
    db.add(new_user)
    db.commit()
    
    # Sau khi đăng ký, quay về trang login
    return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)