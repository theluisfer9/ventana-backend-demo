from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from api.v1.config.database import get_sync_db_pg, get_ch_client
from api.v1.dependencies.auth_dependency import get_current_active_user
from api.v1.models.user import User
from api.v1.models.data_source import DataSource, SavedQuery, RoleDataSource
from api.v1.schemas.query_builder import (
    QueryExecuteRequest, QueryExecuteResponse, ColumnMeta,
    SavedQueryCreate, SavedQueryUpdate, SavedQueryOut, SavedQueryListItem,
)
from api.v1.services.query_engine.validators import validate_columns, validate_filters, validate_group_by, validate_aggregations
from api.v1.services.query_engine.engine import execute_query
from api.v1.auth.permissions import RoleCode

router = APIRouter(prefix="/queries", tags=["Query Builder"])


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
    return user.role and user.role.code == RoleCode.ADMIN


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
        has_access = db.query(RoleDataSource).filter(
            RoleDataSource.role_id == user.role_id,
            RoleDataSource.datasource_id == ds.id,
        ).first()
        if not has_access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene acceso a este DataSource")
    return ds


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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db_pg),
):
    query = db.query(DataSource).options(joinedload(DataSource.columns_def)).filter(DataSource.is_active == True)
    if not _is_admin(current_user):
        accessible_ids = db.query(RoleDataSource.datasource_id).filter(
            RoleDataSource.role_id == current_user.role_id,
        ).subquery()
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
    current_user: User = Depends(get_current_active_user),
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


@router.post("/saved", status_code=status.HTTP_201_CREATED)
def save_query(
    body: SavedQueryCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db_pg),
):
    ds = _get_user_datasource(body.datasource_id, current_user, db)
    validate_columns(body.selected_columns, ds.columns_def)
    filters_dicts = [f.model_dump() for f in body.filters]
    validate_filters(filters_dicts, ds.columns_def)

    # Only admins can share queries to institutions
    institution_id = None
    is_shared = False
    if body.is_shared and body.institution_id:
        if not _is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden compartir consultas a instituciones",
            )
        institution_id = body.institution_id
        is_shared = True

    sq = SavedQuery(
        user_id=current_user.id,
        datasource_id=ds.id,
        name=body.name,
        description=body.description,
        selected_columns=body.selected_columns,
        filters=filters_dicts,
        group_by=body.group_by or [],
        aggregations=[a.model_dump() for a in body.aggregations] if body.aggregations else [],
        institution_id=institution_id,
        is_shared=is_shared,
    )
    db.add(sq)
    db.commit()
    db.refresh(sq)
    return {"id": str(sq.id), "name": sq.name, "is_shared": sq.is_shared}


@router.get("/saved")
def list_saved_queries(
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
    current_user: User = Depends(get_current_active_user),
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
    if sq.user_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para editar esta consulta")

    # Validar columnas, filtros y group_by si se actualizan
    if body.selected_columns is not None or body.filters is not None or body.group_by is not None:
        ds = _get_user_datasource(sq.datasource_id, current_user, db)
        if body.selected_columns is not None:
            validate_columns(body.selected_columns, ds.columns_def)
        if body.filters is not None:
            filters_dicts = [f.model_dump() for f in body.filters]
            validate_filters(filters_dicts, ds.columns_def)
        if body.group_by is not None and body.group_by:
            validate_group_by(body.group_by, ds.columns_def)

    # Aplicar cambios
    update_data = body.model_dump(exclude_unset=True)

    if "filters" in update_data:
        update_data["filters"] = [f.model_dump() for f in body.filters]
    if "aggregations" in update_data and body.aggregations is not None:
        update_data["aggregations"] = [a.model_dump() for a in body.aggregations]

    # Solo admin puede compartir
    if "is_shared" in update_data or "institution_id" in update_data:
        if not _is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo administradores pueden compartir consultas a instituciones",
            )

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
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_sync_db_pg),
):
    sq = db.query(SavedQuery).filter(SavedQuery.id == query_id).first()
    if not sq:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consulta no encontrada")
    # Only the creator or admin can delete
    if sq.user_id != current_user.id and not _is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tiene permiso para eliminar esta consulta")
    db.delete(sq)
    db.commit()


@router.post("/saved/{query_id}/execute", response_model=QueryExecuteResponse)
def execute_saved_query(
    query_id: UUID,
    current_user: User = Depends(get_current_active_user),
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
        client, ds, validated_cols, sq.filters or [], 0, 20,
        group_by=sq.group_by or None,
        aggregations=sq.aggregations or None,
    )

    columns_meta = _build_columns_meta(sq.group_by or None, sq.aggregations or None, ds.columns_def, validated_cols)

    return QueryExecuteResponse(
        items=rows, total=total, offset=0, limit=20, columns_meta=columns_meta,
    )
