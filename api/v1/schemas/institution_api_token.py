from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InstitutionApiTokenCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class InstitutionApiTokenOut(BaseModel):
    id: UUID
    institution_id: UUID
    name: str
    token_prefix: str
    is_active: bool
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstitutionApiTokenCreated(InstitutionApiTokenOut):
    token: str
