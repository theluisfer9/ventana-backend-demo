from pydantic import BaseModel, field_validator
from typing import Optional
from uuid import UUID


ALLOWED_OPERATORS = {"eq", "neq", "gt", "lt", "gte", "lte", "like", "in"}
ALLOWED_AGGREGATIONS = {"COUNT", "SUM"}


class Aggregation(BaseModel):
    column: str
    function: str

    @field_validator("function")
    @classmethod
    def validate_function(cls, v: str) -> str:
        v = v.upper()
        if v not in ALLOWED_AGGREGATIONS:
            raise ValueError(f"Función no soportada: {v}. Permitidas: {ALLOWED_AGGREGATIONS}")
        return v


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
    group_by: list[str] = []
    aggregations: list[Aggregation] = []
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
    description: Optional[str] = None
    selected_columns: list[str]
    filters: list[QueryFilter] = []
    group_by: list[str] = []
    aggregations: list[Aggregation] = []
    institution_id: Optional[UUID] = None
    is_shared: bool = False


class SavedQueryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    selected_columns: Optional[list[str]] = None
    filters: Optional[list[QueryFilter]] = None
    group_by: Optional[list[str]] = None
    aggregations: Optional[list[Aggregation]] = None
    institution_id: Optional[UUID] = None
    is_shared: Optional[bool] = None


class SavedQueryOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    datasource_id: UUID
    datasource_name: str = ""
    selected_columns: list[str]
    filters: list[dict]
    group_by: list[str] = []
    aggregations: list[dict] = []
    institution_id: Optional[UUID] = None
    institution_name: Optional[str] = None
    is_shared: bool = False
    created_by: Optional[str] = None
    created_at: str = ""

    class Config:
        from_attributes = True


class SavedQueryListItem(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    datasource_name: str = ""
    column_count: int = 0
    filter_count: int = 0
    has_aggregations: bool = False
    institution_name: Optional[str] = None
    is_shared: bool = False
    created_by: Optional[str] = None
    created_at: str = ""
