from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID


ALLOWED_OPERATORS = {"eq", "neq", "gt", "lt", "gte", "lte", "like", "in"}


class QueryFilter(BaseModel):
    column: str
    op: str
    value: str | int | float | bool | list

    @field_validator("op")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        if v not in ALLOWED_OPERATORS:
            raise ValueError(f"Operador no soportado: {v}. Permitidos: {ALLOWED_OPERATORS}")
        return v


class QueryExecuteRequest(BaseModel):
    datasource_id: UUID
    columns: list[str]
    filters: list[QueryFilter] = []
    offset: int = 0
    limit: int = 20


class ColumnMeta(BaseModel):
    column_name: str
    label: str
    data_type: str


class QueryExecuteResponse(BaseModel):
    items: list[dict]
    total: int
    offset: int
    limit: int
    columns_meta: list[ColumnMeta]


class SavedQueryCreate(BaseModel):
    datasource_id: UUID
    name: str
    selected_columns: list[str]
    filters: list[QueryFilter] = []


class SavedQueryUpdate(BaseModel):
    name: Optional[str] = None
    selected_columns: Optional[list[str]] = None
    filters: Optional[list[QueryFilter]] = None


class SavedQueryOut(BaseModel):
    id: UUID
    name: str
    datasource_id: UUID
    datasource_name: str = ""
    selected_columns: list[str]
    filters: list[dict]
    created_at: str = ""

    class Config:
        from_attributes = True


class SavedQueryListItem(BaseModel):
    id: UUID
    name: str
    datasource_name: str = ""
    column_count: int = 0
    filter_count: int = 0
    created_at: str = ""
