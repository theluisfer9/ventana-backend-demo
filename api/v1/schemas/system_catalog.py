from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SystemCatalogBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None


class SystemCatalogCreate(SystemCatalogBase):
    pass


class SystemCatalogUpdate(BaseModel):
    code: str | None = Field(None, min_length=2, max_length=100)
    name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = None
    is_active: bool | None = None


class SystemCatalogOut(SystemCatalogBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class SystemCatalogItemBase(BaseModel):
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    value: dict[str, Any] = Field(default_factory=dict)
    display_order: int = 0


class SystemCatalogItemCreate(SystemCatalogItemBase):
    pass


class SystemCatalogItemUpdate(BaseModel):
    code: str | None = Field(None, min_length=2, max_length=100)
    name: str | None = Field(None, min_length=2, max_length=200)
    description: str | None = None
    value: dict[str, Any] | None = None
    display_order: int | None = None
    is_active: bool | None = None


class SystemCatalogItemOut(SystemCatalogItemBase):
    id: UUID
    catalog_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)
