from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query as QueryParam
from sqlalchemy.orm import Session, joinedload
from api.v1.config.database import get_sync_db_pg, get_ch_client
from api.v1.services.query_engine.engine import _safe_identifier
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.dependencies.auth_dependency import get_current_active_user
from api.v1.auth.permissions import PermissionCode
from api.v1.models.user import User
from api.v1.models.data_source import DataSource, DataSourceColumn, ColumnDataType, ColumnCategory
from api.v1.schemas.data_source import (
    DataSourceCreate, DataSourceUpdate, DataSourceOut, DataSourceListItem,
    DataSourceColumnCreate, DataSourceColumnUpdate, DataSourceColumnOut,
)

router = APIRouter(prefix="/datasources", tags=["DataSources (Admin)"])


def _is_admin(user: User) -> bool:
    if not user.role:
        return False
    user_permissions = {p.code for p in user.role.permissions}
    return PermissionCode.SYSTEM_CONFIG.value in user_permissions


def _get_datasource(ds_id: UUID, db: Session) -> DataSource:
    ds = db.query(DataSource).options(joinedload(DataSource.columns_def)).filter(DataSource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DataSource no encontrado")
    return ds


@router.get("/", response_model=list[DataSourceListItem])
def list_datasources(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db_pg),
):
    query = db.query(DataSource).options(joinedload(DataSource.columns_def))
    if not _is_admin(current_user):
        if current_user.institution_id:
            query = query.filter(DataSource.institution_id == current_user.institution_id)
        else:
            query = query.filter(DataSource.id == None)  # no institution, no access
    sources = query.order_by(DataSource.code).all()
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


# ClickHouse type -> app ColumnDataType mapping
_CH_TYPE_MAP = {
    "String": ColumnDataType.TEXT,
    "FixedString": ColumnDataType.TEXT,
    "LowCardinality(String)": ColumnDataType.TEXT,
    "Nullable(String)": ColumnDataType.TEXT,
    "UUID": ColumnDataType.TEXT,
    "Date": ColumnDataType.TEXT,
    "DateTime": ColumnDataType.TEXT,
    "UInt8": ColumnDataType.INTEGER,
    "UInt16": ColumnDataType.INTEGER,
    "UInt32": ColumnDataType.INTEGER,
    "UInt64": ColumnDataType.INTEGER,
    "Int8": ColumnDataType.INTEGER,
    "Int16": ColumnDataType.INTEGER,
    "Int32": ColumnDataType.INTEGER,
    "Int64": ColumnDataType.INTEGER,
    "Nullable(UInt8)": ColumnDataType.INTEGER,
    "Nullable(UInt16)": ColumnDataType.INTEGER,
    "Nullable(UInt32)": ColumnDataType.INTEGER,
    "Nullable(UInt64)": ColumnDataType.INTEGER,
    "Nullable(Int8)": ColumnDataType.INTEGER,
    "Nullable(Int16)": ColumnDataType.INTEGER,
    "Nullable(Int32)": ColumnDataType.INTEGER,
    "Nullable(Int64)": ColumnDataType.INTEGER,
    "Float32": ColumnDataType.FLOAT,
    "Float64": ColumnDataType.FLOAT,
    "Nullable(Float32)": ColumnDataType.FLOAT,
    "Nullable(Float64)": ColumnDataType.FLOAT,
    "Decimal": ColumnDataType.FLOAT,
}


def _map_ch_type(ch_type: str) -> ColumnDataType:
    """Map a ClickHouse type string to ColumnDataType."""
    if ch_type in _CH_TYPE_MAP:
        return _CH_TYPE_MAP[ch_type]
    lower = ch_type.lower()
    if "int" in lower:
        return ColumnDataType.INTEGER
    if "float" in lower or "decimal" in lower:
        return ColumnDataType.FLOAT
    return ColumnDataType.TEXT


def _guess_category(col_name: str, data_type: ColumnDataType) -> ColumnCategory:
    """Guess column category from name and type."""
    name_lower = col_name.lower()
    geo_keywords = ["departamento", "municipio", "lugar_poblado", "codigo_dep", "codigo_mun", "latitud", "longitud"]
    if any(kw in name_lower for kw in geo_keywords):
        return ColumnCategory.GEO
    intervention_keywords = ["bono", "beca", "programa", "intervencion", "beneficio"]
    if any(kw in name_lower for kw in intervention_keywords):
        return ColumnCategory.INTERVENTION
    if data_type in (ColumnDataType.INTEGER, ColumnDataType.FLOAT) and not name_lower.endswith("_id"):
        return ColumnCategory.MEASURE
    return ColumnCategory.DIMENSION


def _make_label(col_name: str) -> str:
    """Convert column_name to a human-readable label."""
    return col_name.replace("_", " ").title()


@router.post("/{ds_id}/auto-discover", response_model=DataSourceOut)
def auto_discover_columns(
    ds_id: UUID,
    current_user: User = Depends(RequirePermission(PermissionCode.DATASOURCES_MANAGE)),
    db: Session = Depends(get_sync_db_pg),
    ch_client=Depends(get_ch_client),
):
    """Auto-discover columns from ClickHouse table and register them in the datasource."""
    ds = _get_datasource(ds_id, db)

    try:
        safe_table = _safe_identifier(ds.ch_table)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Nombre de tabla no válido: {ds.ch_table!r}")

    result = ch_client.query(f"DESCRIBE TABLE {safe_table}")

    # Get existing column names to avoid duplicates
    existing_names = {c.column_name for c in (ds.columns_def or [])}

    new_count = 0
    for i, row in enumerate(result.result_rows):
        col_name = row[0]
        ch_type = row[1]

        if col_name in existing_names:
            continue

        data_type = _map_ch_type(ch_type)
        category = _guess_category(col_name, data_type)

        col = DataSourceColumn(
            datasource_id=ds.id,
            column_name=col_name,
            label=_make_label(col_name),
            data_type=data_type,
            category=category,
            is_selectable=True,
            is_filterable=True,
            is_groupable=(category in (ColumnCategory.DIMENSION, ColumnCategory.GEO, ColumnCategory.INTERVENTION)),
            display_order=len(existing_names) + i,
        )
        db.add(col)
        new_count += 1

    db.commit()
    db.refresh(ds)
    return _datasource_to_out(ds)


@router.get("/{ds_id}", response_model=DataSourceOut)
def get_datasource(
    ds_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db_pg),
):
    ds = _get_datasource(ds_id, db)
    if not _is_admin(current_user):
        if not (current_user.institution_id and ds.institution_id and current_user.institution_id == ds.institution_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene acceso a este DataSource")
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
