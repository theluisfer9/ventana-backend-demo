from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query as QueryParam
from sqlalchemy.orm import Session, joinedload
from api.v1.config.database import get_sync_db_pg, get_ch_client
from api.v1.services.query_engine.engine import _safe_identifier
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.auth.permissions import PermissionCode
from api.v1.models.user import User
from api.v1.models.data_source import DataSource, DataSourceColumn, ColumnDataType, ColumnCategory
from api.v1.schemas.data_source import (
    DataSourceCreate, DataSourceUpdate, DataSourceOut, DataSourceListItem,
    DataSourceColumnCreate, DataSourceColumnUpdate, DataSourceColumnOut,
)

router = APIRouter(prefix="/datasources", tags=["DataSources (Admin)"])


def _get_datasource(ds_id: UUID, db: Session) -> DataSource:
    ds = db.query(DataSource).options(joinedload(DataSource.columns_def)).filter(DataSource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DataSource no encontrado")
    return ds


@router.get("/", response_model=list[DataSourceListItem])
def list_datasources(
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
):
    sources = db.query(DataSource).options(joinedload(DataSource.columns_def)).order_by(DataSource.code).all()
    return [
        DataSourceListItem(
            id=ds.id,
            code=ds.code,
            name=ds.name,
            ch_table=ds.ch_table,
            base_filter_columns=ds.base_filter_columns or [],
            is_active=ds.is_active,
            column_count=len(ds.columns_def) if ds.columns_def else 0,
        )
        for ds in sources
    ]


@router.post("/", response_model=DataSourceOut, status_code=status.HTTP_201_CREATED)
def create_datasource(
    body: DataSourceCreate,
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
):
    existing = db.query(DataSource).filter(DataSource.code == body.code).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"DataSource '{body.code}' ya existe")
    ds = DataSource(**body.model_dump())
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return _datasource_to_out(ds)


@router.get("/ch-tables", response_model=list[str])
def list_ch_tables(
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    ch_client=Depends(get_ch_client),
):
    """List available ClickHouse tables for auto-discovery."""
    result = ch_client.query("SHOW TABLES FROM rsh")
    tables = [f"rsh.{row[0]}" for row in result.result_rows]
    return tables


@router.get("/ch-columns")
def list_ch_columns(
    table: str = QueryParam(..., description="Fully qualified table name, e.g. rsh.vw_beneficios_x_hogar"),
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    ch_client=Depends(get_ch_client),
):
    """List columns of a ClickHouse table."""
    try:
        safe_table = _safe_identifier(table)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Nombre de tabla no válido: {table!r}")
    result = ch_client.query(f"DESCRIBE TABLE {safe_table}")
    columns = [
        {"name": row[0], "type": row[1]}
        for row in result.result_rows
    ]
    return columns


@router.get("/{ds_id}", response_model=DataSourceOut)
def get_datasource(
    ds_id: UUID,
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
):
    ds = _get_datasource(ds_id, db)
    return _datasource_to_out(ds)


@router.put("/{ds_id}", response_model=DataSourceOut)
def update_datasource(
    ds_id: UUID,
    body: DataSourceUpdate,
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
):
    ds = _get_datasource(ds_id, db)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(ds, key, value)
    db.commit()
    db.refresh(ds)
    return _datasource_to_out(ds)


@router.delete("/{ds_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_datasource(
    ds_id: UUID,
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
):
    ds = _get_datasource(ds_id, db)
    ds.is_active = False
    db.commit()


@router.post("/{ds_id}/columns", response_model=DataSourceColumnOut, status_code=status.HTTP_201_CREATED)
def create_column(
    ds_id: UUID,
    body: DataSourceColumnCreate,
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
):
    ds = _get_datasource(ds_id, db)
    col = DataSourceColumn(
        datasource_id=ds.id,
        column_name=body.column_name,
        label=body.label,
        data_type=ColumnDataType(body.data_type),
        category=ColumnCategory(body.category),
        is_selectable=body.is_selectable,
        is_filterable=body.is_filterable,
        is_groupable=body.is_groupable,
        display_order=body.display_order,
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return _column_to_out(col)


@router.put("/{ds_id}/columns/{col_id}", response_model=DataSourceColumnOut)
def update_column(
    ds_id: UUID,
    col_id: UUID,
    body: DataSourceColumnUpdate,
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
):
    col = db.query(DataSourceColumn).filter(
        DataSourceColumn.id == col_id,
        DataSourceColumn.datasource_id == ds_id,
    ).first()
    if not col:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Columna no encontrada")
    for key, value in body.model_dump(exclude_unset=True).items():
        if key == "data_type" and value:
            value = ColumnDataType(value)
        if key == "category" and value:
            value = ColumnCategory(value)
        setattr(col, key, value)
    db.commit()
    db.refresh(col)
    return _column_to_out(col)


@router.delete("/{ds_id}/columns/{col_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_column(
    ds_id: UUID,
    col_id: UUID,
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
):
    col = db.query(DataSourceColumn).filter(
        DataSourceColumn.id == col_id,
        DataSourceColumn.datasource_id == ds_id,
    ).first()
    if not col:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Columna no encontrada")
    db.delete(col)
    db.commit()


def _datasource_to_out(ds: DataSource) -> DataSourceOut:
    return DataSourceOut(
        id=ds.id,
        code=ds.code,
        name=ds.name,
        ch_table=ds.ch_table,
        base_filter_columns=ds.base_filter_columns or [],
        base_filter_logic=ds.base_filter_logic or "OR",
        institution_id=ds.institution_id,
        is_active=ds.is_active,
        columns=[_column_to_out(c) for c in (ds.columns_def or [])],
    )


def _column_to_out(col: DataSourceColumn) -> DataSourceColumnOut:
    return DataSourceColumnOut(
        id=col.id,
        column_name=col.column_name,
        label=col.label,
        description=col.description,
        data_type=col.data_type.value if col.data_type else "TEXT",
        category=col.category.value if col.category else "DIMENSION",
        is_selectable=col.is_selectable,
        is_filterable=col.is_filterable,
        is_groupable=col.is_groupable,
        display_order=col.display_order,
    )
