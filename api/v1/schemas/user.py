from pydantic import BaseModel, ConfigDict, Field, EmailStr
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from api.v1.schemas.role import RoleMinimal
from api.v1.schemas.institution import InstitutionMinimal


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    role_id: UUID
    institution_id: Optional[UUID] = None


class UserCreateByAdmin(UserBase):
    """Admin can create users without password (for Keycloak users)"""
    password: Optional[str] = Field(None, min_length=8, max_length=128)
    role_id: UUID
    institution_id: Optional[UUID] = None
    is_active: bool = True
    is_verified: bool = False
    keycloak_id: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=100)
    first_name: Optional[str] = Field(None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)
    role_id: Optional[UUID] = None
    institution_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class UserOut(UserBase):
    id: UUID
    role: RoleMinimal
    institution: Optional[InstitutionMinimal] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserMinimal(BaseModel):
    """Minimal user info for nested responses"""
    id: UUID
    username: str
    email: EmailStr
    full_name: str

    model_config = ConfigDict(from_attributes=True)


class UserFilters(BaseModel):
    """Filters for user listing"""
    role_id: Optional[UUID] = None
    institution_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None
    search: Optional[str] = None
    created_from: Optional[date] = None
    created_to: Optional[date] = None


class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordReset(BaseModel):
    """Schema for password reset confirmation"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)


class PasswordResetRequest(BaseModel):
    """Schema for password reset request"""
    email: EmailStr
