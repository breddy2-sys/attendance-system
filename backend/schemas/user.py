"""Pydantic schemas for user authentication."""

from pydantic import BaseModel, EmailStr, Field
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    """User role enumeration."""
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"


class UserCreate(BaseModel):
    """User creation schema."""
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    role: UserRole = UserRole.STUDENT


class UserUpdate(BaseModel):
    """User update schema."""
    full_name: str | None = Field(None, min_length=2, max_length=255)
    email: EmailStr | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    """User response schema."""
    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str
