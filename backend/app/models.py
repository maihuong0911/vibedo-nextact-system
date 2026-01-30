from sqlalchemy import Column, Integer, String, Text, ForeignKey, Date, TIMESTAMP, Boolean
from sqlalchemy.sql import func
from .database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    full_name = Column(String)
    email = Column(String, unique=True)
    password_hash = Column(Text)
    created_at = Column(TIMESTAMP, server_default=func.now())

class Note(Base):
    __tablename__ = "notes"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    content = Column(Text)
    status = Column(String, default="todo")
    priority = Column(Integer, default=1)
    due_date = Column(Date)
    is_quick_add = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())