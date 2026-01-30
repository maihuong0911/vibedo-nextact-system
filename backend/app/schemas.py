from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str

class NoteCreate(BaseModel):
    title: str
    content: Optional[str] = None