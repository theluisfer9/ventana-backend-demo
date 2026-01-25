from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Schema for token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""
    refresh_token: str


class TokenPayload(BaseModel):
    """Schema for decoded token payload"""
    sub: str  # user_id
    exp: datetime
    iat: datetime
    jti: str  # token unique id
    type: str  # "access" or "refresh"
    role: Optional[str] = None


class CurrentUser(BaseModel):
    """Schema for current authenticated user info"""
    id: UUID
    email: str
    username: str
    first_name: str
    last_name: str
    full_name: str
    role_code: str
    role_name: str
    institution_code: Optional[str] = None
    institution_name: Optional[str] = None
    permissions: list[str] = []


class SessionInfo(BaseModel):
    """Schema for session information"""
    id: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False


class ProfileUpdate(BaseModel):
    """Schema for updating own profile"""
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
