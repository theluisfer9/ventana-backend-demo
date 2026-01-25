from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from api.v1.schemas.permission import PermissionMinimal


class RoleBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class RoleCreate(RoleBase):
    permission_ids: Optional[List[UUID]] = None


class RoleUpdate(BaseModel):
    code: Optional[str] = Field(None, min_length=2, max_length=50)
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None


class RoleOut(RoleBase):
    id: UUID
    is_system: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    permissions: List[PermissionMinimal] = []

    model_config = ConfigDict(from_attributes=True)


class RoleMinimal(BaseModel):
    """Minimal role info for nested responses"""
    id: UUID
    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class RolePermissionsUpdate(BaseModel):
    """Schema for updating role permissions"""
    permission_ids: List[UUID]
