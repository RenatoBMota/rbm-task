from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from app.models.user import UserRole


class UserBase(BaseModel):
    email: EmailStr
    full_name: str


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=72)


class UserUpdate(BaseModel):
    full_name: str | None = None
    avatar_url: str | None = None


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserOut(UserBase):
    id: int
    is_active: bool
    role: UserRole
    avatar_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
