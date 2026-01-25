from pydantic import BaseModel, ConfigDict, Field
from typing import Optional
from datetime import datetime
from uuid import UUID


class PermissionBase(BaseModel):
    code: str = Field(..., min_length=3, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    module: str = Field(..., min_length=2, max_length=50)


class PermissionCreate(PermissionBase):
    pass


class PermissionOut(PermissionBase):
    id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionMinimal(BaseModel):
    """Minimal permission info for nested responses"""
    id: UUID
    code: str
    name: str
    module: str

    model_config = ConfigDict(from_attributes=True)
