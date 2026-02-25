from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class DataSourceColumnCreate(BaseModel):
    column_name: str
    label: str
    description: Optional[str] = None
    data_type: str = "TEXT"
    category: str = "DIMENSION"
    is_selectable: bool = True
    is_filterable: bool = True
    display_order: int = 0


class DataSourceColumnUpdate(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    data_type: Optional[str] = None
    category: Optional[str] = None
    is_selectable: Optional[bool] = None
    is_filterable: Optional[bool] = None
    display_order: Optional[int] = None


class DataSourceColumnOut(BaseModel):
    id: UUID
    column_name: str
    label: str
    description: Optional[str] = None
    data_type: str
    category: str
    is_selectable: bool
    is_filterable: bool
    is_groupable: bool = False
    display_order: int

    class Config:
        from_attributes = True


class DataSourceCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    ch_table: str
    base_filter: Optional[str] = None
    institution_id: Optional[UUID] = None


class DataSourceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    ch_table: Optional[str] = None
    base_filter: Optional[str] = None
    institution_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class DataSourceOut(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    ch_table: str
    base_filter: Optional[str] = None
    institution_id: Optional[UUID] = None
    is_active: bool
    columns: list[DataSourceColumnOut] = []

    class Config:
        from_attributes = True


class DataSourceListItem(BaseModel):
    id: UUID
    code: str
    name: str
    description: Optional[str] = None
    is_active: bool
    column_count: int = 0

    class Config:
        from_attributes = True
