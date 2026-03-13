from uuid import UUID
from datetime import datetime
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from api.v1.config.database import get_sync_db_pg, get_ch_client
from api.v1.dependencies.auth_dependency import get_current_active_user
from api.v1.dependencies.permission_dependency import RequireAnyPermission
from api.v1.models.user import User
from api.v1.models.data_source import DataSource, SavedQuery, RoleDataSource
from api.v1.schemas.query_builder import (
    QueryExecuteRequest, QueryExecuteResponse, ColumnMeta,
    SavedQueryCreate, SavedQueryUpdate, SavedQueryOut, SavedQueryListItem,
)
from api.v1.services.query_engine.validators import validate_columns, validate_filters, validate_group_by, validate_aggregations
from api.v1.services.query_engine.engine import execute_query
from api.v1.services.query_engine.export import (
    generate_csv_streaming as gen_query_csv_stream,
    generate_excel as gen_query_excel,
    generate_pdf as gen_query_pdf,
)
from api.v1.auth.permissions import PermissionCode


class ExportFormat(str, Enum):
    csv = "csv"
    excel = "excel"
    pdf = "pdf"

router = APIRouter(prefix="/queries", tags=["Query Builder"])

# Permission guard: read-only query routes (list, execute)
_query_permission = RequireAnyPermission([
    PermissionCode.DATABASES_READ,
    PermissionCode.REPORTS_READ,
])

# Permission guard: create/edit/delete saved queries
_query_write_permission = RequireAnyPermission([
    PermissionCode.REPORTS_CREATE,
])


def _build_columns_meta(
    group_by: list[str] | None,
    aggregations: list[dict] | None,
    columns_def: list,
    validated_cols: list,
) -> list[ColumnMeta]:
    """Build columns_meta for response, handling both grouped and non-grouped queries."""
    if group_by and aggregations:
        col_map = {c.column_name: c for c in columns_def}
        meta = []
        for name in group_by:
            c = col_map[name]
            meta.append(ColumnMeta(column_name=c.column_name, label=c.label, data_type=c.data_type.value))
        for agg in aggregations:
            func = agg["function"].upper()
            col = agg["column"]
            if col == "*":
                meta.append(ColumnMeta(column_name="count", label="Conteo", data_type="INTEGER"))
            else:
                alias = f"{func.lower()}_{col}"
                orig = col_map.get(col)
                label = f"{func}({orig.label if orig else col})"
                meta.append(ColumnMeta(column_name=alias, label=label, data_type="FLOAT" if func == "SUM" else "INTEGER"))
        return meta
    return [
        ColumnMeta(column_name=c.column_name, label=c.label, data_type=c.data_type.value)
        for c in validated_cols
    ]


def _is_admin(user: User) -> bool:
    if not user.role:
        return False
    user_permissions = {p.code for p in user.role.permissions}
    return PermissionCode.SYSTEM_CONFIG.value in user_permissions


def _get_user_datasource(ds_id: UUID, user: User, db: Session) -> DataSource:
    ds = (
        db.query(DataSource)
        .options(joinedload(DataSource.columns_def))
        .filter(DataSource.id == ds_id, DataSource.is_active == True)
        .first()
    )
    if not ds:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DataSource no encontrado")
    if not _is_admin(user):
        # Allow access if datasource belongs to user's institution
        if user.institution_id and ds.institution_id and user.institution_id == ds.institution_id:
            return ds
        # Otherwise check role-datasource mapping
        has_access = db.query(RoleDataSource).filter(
            RoleDataSource.role_id == user.role_id,
            RoleDataSource.datasource_id == ds.id,
        ).first()
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene acceso a este DataSource")
    return ds


def _is_institutional_admin(user: User) -> bool:
    """Check if user has reports:create (admin institucional)."""
    if not user.role:
        return False
    user_permissions = {p.code for p in user.role.permissions}
    return PermissionCode.REPORTS_CREATE.value in user_permissions


def _same_institution(sq: SavedQuery, user: User) -> bool:
    """Check if saved query's datasource belongs to user's institution."""
    if not user.institution_id:
        return False
    if sq.institution_id and sq.institution_id == user.institution_id:
        return True
    if sq.data_source and sq.data_source.institution_id == user.institution_id:
        return True
    return False


def _normalize_saved_query_scope(
    institution_id,
    is_shared: bool,
    current_user: User,
):
    """Normalize sharing fields to keep private queries private."""
    if _is_admin(current_user):
        if is_shared:
            if not institution_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Las consultas compartidas requieren una institucion destino",
                )
            return institution_id, True
        return None, False

    if _is_institutional_admin(current_user) and current_user.institution_id:
        if is_shared:
            target_inst = institution_id or current_user.institution_id
            if str(target_inst) != str(current_user.institution_id):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo puede compartir consultas dentro de su institucion",
                )
            return current_user.institution_id, True
        return None, False

    if is_shared or institution_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permiso para compartir consultas a instituciones",
        )
    return None, False


def _can_access_saved_query(sq: SavedQuery, user: User) -> bool:
    """Check if user can access a saved query."""
    if _is_admin(user):
        return True
    if sq.user_id == user.id:
        return True
    if sq.is_shared and sq.institution_id and user.institution_id == sq.institution_id:
        return True
    return False


@router.get("/datasources")
def list_available_datasources(
    current_user: User = Depends(_query_permission),
    db: Session = Depends(get_sync_db_pg),
):
    query = db.query(DataSource).options(joinedload(DataSource.columns_def)).filter(DataSource.is_active == True)
    if not _is_admin(current_user):
        accessible_ids = db.query(RoleDataSource.datasource_id).filter(
            RoleDataSource.role_id == current_user.role_id,
        ).subquery()
        if current_user.institution_id:
            query = query.filter(
                or_(
                    DataSource.id.in_(accessible_ids),
                    DataSource.institution_id == current_user.institution_id,
                )
            )
        else:
            query = query.filter(DataSource.id.in_(accessible_ids))
    sources = query.order_by(DataSource.name).all()
    return [
        {
            "id": str(ds.id),
            "code": ds.code,
            "name": ds.name,
            "description": ds.description,
            "columns": [
                {
                    "column_name": c.column_name,
                    "label": c.label,
                    "description": c.description,
                    "data_type": c.data_type.value,
                    "category": c.category.value,
                    "is_selectable": c.is_selectable,
                    "is_filterable": c.is_filterable,
                    "is_groupable": c.is_groupable,
                }
                for c in sorted(ds.columns_def or [], key=lambda x: x.display_order)
            ],
        }
        for ds in sources
    ]


@router.post("/execute", response_model=QueryExecuteResponse)
def execute_adhoc_query(
    body: QueryExecuteRequest,
    current_user: User = Depends(_query_permission),
    db: Session = Depends(get_sync_db_pg),
    client=Depends(get_ch_client),
):
    ds = _get_user_datasource(body.datasource_id, current_user, db)
    validated_cols = validate_columns(body.columns, ds.columns_def)
    filters_dicts = [f.model_dump() for f in body.filters]
    validate_filters(filters_dicts, ds.columns_def)

    # Validate GROUP BY + aggregations (must be both or neither)
    group_by_names = body.group_by or []
    agg_dicts = [a.model_dump() for a in body.aggregations] if body.aggregations else []
    if bool(group_by_names) != bool(agg_dicts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by y aggregations deben proporcionarse juntos",
        )
    if group_by_names:
        validate_group_by(group_by_names, ds.columns_def)
    if agg_dicts:
        validate_aggregations(agg_dicts, ds.columns_def)

    rows, total = execute_query(
        client, ds, validated_cols, filters_dicts, body.offset, body.limit,
        group_by=group_by_names or None,
        aggregations=agg_dicts or None,
    )

    columns_meta = _build_columns_meta(group_by_names or None, agg_dicts or None, ds.columns_def, validated_cols)

    return QueryExecuteResponse(
        items=rows, total=total, offset=body.offset, limit=body.limit, columns_meta=columns_meta,
    )


_MEDIA_TYPES = {
    "csv": "text/csv; charset=utf-8",
    "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}
_EXTENSIONS = {"csv": "csv", "excel": "xlsx", "pdf": "pdf"}


@router.post("/execute/export")
def export_adhoc_query(
    body: QueryExecuteRequest,
    formato: ExportFormat = Query(..., description="Formato de exportacion: csv, excel, pdf"),
    current_user: User = Depends(_query_permission),
    db: Session = Depends(get_sync_db_pg),
    client=Depends(get_ch_client),
):
    """Ejecutar una consulta ad-hoc y descargar el resultado como CSV, Excel o PDF."""
    ds = _get_user_datasource(body.datasource_id, current_user, db)
    validated_cols = validate_columns(body.columns, ds.columns_def)
    filters_dicts = [f.model_dump() for f in body.filters]
    validate_filters(filters_dicts, ds.columns_def)

    group_by_names = body.group_by or []
    agg_dicts = [a.model_dump() for a in body.aggregations] if body.aggregations else []
    if bool(group_by_names) != bool(agg_dicts):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by y aggregations deben proporcionarse juntos",
        )
    if group_by_names:
        validate_group_by(group_by_names, ds.columns_def)
    if agg_dicts:
        validate_aggregations(agg_dicts, ds.columns_def)

    rows, _ = execute_query(
        client, ds, validated_cols, filters_dicts, 0, 2_000_000_000,
        group_by=group_by_names or None,
        aggregations=agg_dicts or None,
    )

    columns_meta = [
        {"column_name": c.column_name, "label": c.label, "data_type": c.data_type}
        for c in _build_columns_meta(group_by_names or None, agg_dicts or None, ds.columns_def, validated_cols)
    ]

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = _EXTENSIONS[formato.value]
    filename = f"consulta_{ts}.{ext}"
    disposition = f'attachment; filename="{filename}"'

    if formato == ExportFormat.csv:
        return StreamingResponse(
            gen_query_csv_stream(rows, columns_meta),
            media_type=_MEDIA_TYPES["csv"],
            headers={"Content-Disposition": disposition},
        )

    if formato == ExportFormat.excel:
        buf = gen_query_excel(rows, columns_meta, title="Consulta")
    else:
        buf = gen_query_pdf(rows, columns_meta, title="Consulta")

    return StreamingResponse(
        buf,
        media_type=_MEDIA_TYPES[formato.value],
        headers={"Content-Disposition": disposition},
    )


@router.post("/saved", status_code=status.HTTP_201_CREATED)
def save_query(
    body: SavedQueryCreate,
    current_user: User = Depends(_query_write_permission),
    db: Session = Depends(get_sync_db_pg),
):
    ds = _get_user_datasource(body.datasource_id, current_user, db)
    validate_columns(body.selected_columns, ds.columns_def)
    filters_dicts = [f.model_dump() for f in body.filters]
    validate_filters(filters_dicts, ds.columns_def)

    # Validate group_by and aggregations on save too
    if bool(body.group_by) != bool(body.aggregations):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="group_by y aggregations deben proporcionarse juntos",
        )
    if body.group_by:
        validate_group_by(body.group_by, ds.columns_def)
    agg_dicts = [a.model_dump() for a in body.aggregations] if body.aggregations else []
    if agg_dicts:
        validate_aggregations(agg_dicts, ds.columns_def)

    institution_id, is_shared = _normalize_saved_query_scope(
        body.institution_id,
        body.is_shared,
        current_user,
    )

    sq = SavedQuery(
        user_id=current_user.id,
        datasource_id=ds.id,
        name=body.name,
        description=body.description,
        selected_columns=body.selected_columns,
        filters=filters_dicts,
        group_by=body.group_by or [],
        aggregations=agg_dicts,
        institution_id=institution_id,
        is_shared=is_shared,
    )
    db.add(sq)
    db.commit()
    db.refresh(sq)
    return {"id": str(sq.id), "name": sq.name, "is_shared": sq.is_shared}


@router.get("/saved")
def list_saved_queries(
    current_user: User = Depends(_query_permission),
    db: Session = Depends(get_sync_db_pg),
):
    """
    List saved queries visible to the current user:
    - Admin: ALL saved queries
    - Institutional user: own queries + shared queries for their institution
    - Other users: only their own queries
    """
    base_query = (
        db.query(SavedQuery)
        .options(
            joinedload(SavedQuery.data_source),
            joinedload(SavedQuery.user),
            joinedload(SavedQuery.institution),
        )
    )

    if _is_admin(current_user):
        queries = base_query.order_by(SavedQuery.created_at.desc()).all()
    elif current_user.institution_id:
        queries = (
            base_query.filter(
                or_(
                    SavedQuery.user_id == current_user.id,
                    (SavedQuery.is_shared == True) & (SavedQuery.institution_id == current_user.institution_id),
                )
            )
            .order_by(SavedQuery.created_at.desc())
            .all()
        )
    else:
        queries = (
            base_query.filter(SavedQuery.user_id == current_user.id)
            .order_by(SavedQuery.created_at.desc())
            .all()
        )

    return [
        SavedQueryListItem(
            id=sq.id,
            name=sq.name,
            description=sq.description,
            datasource_name=sq.data_source.name if sq.data_source else "",
            column_count=len(sq.selected_columns) if sq.selected_columns else 0,
            filter_count=len(sq.filters) if sq.filters else 0,
            has_aggregations=bool(sq.aggregations),
            institution_name=sq.institution.name if sq.institution else None,
            is_shared=sq.is_shared or False,
            created_by=sq.user.full_name if sq.user else None,
            created_at=sq.created_at.isoformat() if sq.created_at else "",
        )
        for sq in queries
    ]


@router.get("/saved/{query_id}")
def get_saved_query(
    query_id: UUID,
    current_user: User = Depends(_query_permission),
    db: Session = Depends(get_sync_db_pg),
):
    sq = (
        db.query(SavedQuery)
        .options(
            joinedload(SavedQuery.data_source),
            joinedload(SavedQuery.user),
            joinedload(SavedQuery.institution),
        )
        .filter(SavedQuery.id == query_id)
        .first()
    )
    if not sq or not _can_access_saved_query(sq, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")
    return SavedQueryOut(
        id=sq.id,
        name=sq.name,
        description=sq.description,
        datasource_id=sq.datasource_id,
        datasource_name=sq.data_source.name if sq.data_source else "",
        selected_columns=sq.selected_columns or [],
        filters=sq.filters or [],
        group_by=sq.group_by or [],
        aggregations=sq.aggregations or [],
        institution_id=sq.institution_id,
        institution_name=sq.institution.name if sq.institution else None,
        is_shared=sq.is_shared or False,
        created_by=sq.user.full_name if sq.user else None,
        created_at=sq.created_at.isoformat() if sq.created_at else "",
    )


@router.put("/saved/{query_id}")
def update_saved_query(
    query_id: UUID,
    body: SavedQueryUpdate,
    current_user: User = Depends(_query_write_permission),
    db: Session = Depends(get_sync_db_pg),
):
    """Actualizar una consulta guardada. Solo el creador o admin pueden editar."""
    sq = (
        db.query(SavedQuery)
        .options(
            joinedload(SavedQuery.data_source),
            joinedload(SavedQuery.user),
            joinedload(SavedQuery.institution),
        )
        .filter(SavedQuery.id == query_id)
        .first()
    )
    if not sq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")
    can_edit = (
        _is_admin(current_user)
        or sq.user_id == current_user.id
        or (_is_institutional_admin(current_user) and _same_institution(sq, current_user))
    )
    if not can_edit:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para editar esta consulta")

    # Validar columnas, filtros, group_by y aggregations si se actualizan
    if body.selected_columns is not None or body.filters is not None or body.group_by is not None or body.aggregations is not None:
        ds = _get_user_datasource(sq.datasource_id, current_user, db)
        if body.selected_columns is not None:
            validate_columns(body.selected_columns, ds.columns_def)
        if body.filters is not None:
            filters_dicts = [f.model_dump() for f in body.filters]
            validate_filters(filters_dicts, ds.columns_def)
        next_group_by = body.group_by if body.group_by is not None else (sq.group_by or [])
        next_aggregations = (
            [a.model_dump() for a in body.aggregations]
            if body.aggregations is not None
            else (sq.aggregations or [])
        )
        if bool(next_group_by) != bool(next_aggregations):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="group_by y aggregations deben proporcionarse juntos",
            )
        if next_group_by:
            validate_group_by(next_group_by, ds.columns_def)
        if next_aggregations:
            validate_aggregations(next_aggregations, ds.columns_def)

    # Aplicar cambios
    update_data = body.model_dump(exclude_unset=True)

    if "filters" in update_data:
        update_data["filters"] = [f.model_dump() for f in body.filters]
    if "aggregations" in update_data and body.aggregations is not None:
        update_data["aggregations"] = [a.model_dump() for a in body.aggregations]

    # Solo admin o admin institucional (dentro de su institucion) puede compartir
    if "is_shared" in update_data or "institution_id" in update_data:
        normalized_institution_id, normalized_is_shared = _normalize_saved_query_scope(
            update_data.get("institution_id", sq.institution_id),
            update_data.get("is_shared", sq.is_shared or False),
            current_user,
        )
        update_data["institution_id"] = normalized_institution_id
        update_data["is_shared"] = normalized_is_shared

    for key, value in update_data.items():
        setattr(sq, key, value)

    db.commit()
    db.refresh(sq)

    return SavedQueryOut(
        id=sq.id,
        name=sq.name,
        description=sq.description,
        datasource_id=sq.datasource_id,
        datasource_name=sq.data_source.name if sq.data_source else "",
        selected_columns=sq.selected_columns or [],
        filters=sq.filters or [],
        group_by=sq.group_by or [],
        aggregations=sq.aggregations or [],
        institution_id=sq.institution_id,
        institution_name=sq.institution.name if sq.institution else None,
        is_shared=sq.is_shared or False,
        created_by=sq.user.full_name if sq.user else None,
        created_at=sq.created_at.isoformat() if sq.created_at else "",
    )


@router.delete("/saved/{query_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_query(
    query_id: UUID,
    current_user: User = Depends(_query_write_permission),
    db: Session = Depends(get_sync_db_pg),
):
    sq = (
        db.query(SavedQuery)
        .options(joinedload(SavedQuery.data_source))
        .filter(SavedQuery.id == query_id)
        .first()
    )
    if not sq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")
    can_delete = (
        _is_admin(current_user)
        or sq.user_id == current_user.id
        or (_is_institutional_admin(current_user) and _same_institution(sq, current_user))
    )
    if not can_delete:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para eliminar esta consulta")
    db.delete(sq)
    db.commit()


@router.post("/saved/{query_id}/execute", response_model=QueryExecuteResponse)
def execute_saved_query(
    query_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=1000),
    current_user: User = Depends(_query_permission),
    db: Session = Depends(get_sync_db_pg),
    client=Depends(get_ch_client),
):
    sq = (
        db.query(SavedQuery)
        .options(joinedload(SavedQuery.data_source))
        .filter(SavedQuery.id == query_id)
        .first()
    )
    if not sq or not _can_access_saved_query(sq, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")

    ds = _get_user_datasource(sq.datasource_id, current_user, db)
    validated_cols = validate_columns(sq.selected_columns, ds.columns_def)
    validate_filters(sq.filters or [], ds.columns_def)

    rows, total = execute_query(
        client, ds, validated_cols, sq.filters or [], offset, limit,
        group_by=sq.group_by or None,
        aggregations=sq.aggregations or None,
    )

    columns_meta = _build_columns_meta(sq.group_by or None, sq.aggregations or None, ds.columns_def, validated_cols)

    return QueryExecuteResponse(
        items=rows, total=total, offset=offset, limit=limit, columns_meta=columns_meta,
    )


# ── Export de consultas guardadas ────────────────────────────────────


@router.get("/saved/{query_id}/export")
def export_saved_query(
    query_id: UUID,
    formato: ExportFormat = Query(..., description="Formato de exportacion: csv, excel, pdf"),
    current_user: User = Depends(_query_permission),
    db: Session = Depends(get_sync_db_pg),
    client=Depends(get_ch_client),
):
    """Exportar una consulta guardada a CSV, Excel o PDF."""
    sq = (
        db.query(SavedQuery)
        .options(joinedload(SavedQuery.data_source))
        .filter(SavedQuery.id == query_id)
        .first()
    )
    if not sq or not _can_access_saved_query(sq, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")

    ds = _get_user_datasource(sq.datasource_id, current_user, db)
    validated_cols = validate_columns(sq.selected_columns, ds.columns_def)
    validate_filters(sq.filters or [], ds.columns_def)

    rows, _ = execute_query(
        client, ds, validated_cols, sq.filters or [], 0, 2_000_000_000,
        group_by=sq.group_by or None,
        aggregations=sq.aggregations or None,
    )

    columns_meta = [
        {"column_name": c.column_name, "label": c.label, "data_type": c.data_type}
        for c in _build_columns_meta(sq.group_by or None, sq.aggregations or None, ds.columns_def, validated_cols)
    ]

    title = sq.name or "Consulta"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = _EXTENSIONS[formato.value]
    safe_name = "".join(c if c.isalnum() or c in "_- " else "_" for c in title).strip()[:50]
    filename = f"{safe_name}_{ts}.{ext}"
    disposition = f'attachment; filename="{filename}"'

    if formato == ExportFormat.csv:
        return StreamingResponse(
            gen_query_csv_stream(rows, columns_meta),
            media_type=_MEDIA_TYPES["csv"],
            headers={"Content-Disposition": disposition},
        )

    if formato == ExportFormat.excel:
        buf = gen_query_excel(rows, columns_meta, title=title)
    else:
        buf = gen_query_pdf(rows, columns_meta, title=title)

    return StreamingResponse(
        buf,
        media_type=_MEDIA_TYPES[formato.value],
        headers={"Content-Disposition": disposition},
    )
