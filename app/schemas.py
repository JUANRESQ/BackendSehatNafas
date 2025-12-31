# app/schemas.py
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from typing import Optional, Generic, TypeVar

# =========================
# AUTH
# =========================
class UserCreate(BaseModel):
    nama: str = Field(..., max_length=120)
    email: EmailStr
    username: str = Field(..., max_length=120)
    password: str = Field(..., min_length=6, max_length=72)

class UserOut(BaseModel):
    id: int
    nama: str
    email: EmailStr
    username: str
    created_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =========================
# ANALYSIS
# =========================
class AnalysisCreate(BaseModel):
    label: str = Field(..., max_length=50)
    confidence: float = Field(..., ge=0.0, le=1.0)
    save_history: bool = True

class AnalysisPreview(BaseModel):
    label: str
    confidence: float

class AnalysisOut(BaseModel):
    id: int
    user_id: int
    label: str
    confidence: float
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# RESPONSE WRAPPER (WAJIB DI BAWAH)
# =========================
T = TypeVar("T")

class ApiResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None

class RegisterResponse(ApiResponse[UserOut]):
    pass

class LoginResponse(ApiResponse[Token]):
    pass
