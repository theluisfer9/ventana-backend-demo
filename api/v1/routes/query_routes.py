from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from api.v1.config.database import get_sync_db_pg, get_ch_client
from api.v1.dependencies.auth_dependency import get_current_active_user
from api.v1.models.user import User
from api.v1.models.data_source import DataSource, SavedQuery
from api.v1.schemas.query_builder import (
    QueryExecuteRequest, QueryExecuteResponse, ColumnMeta,
    SavedQueryCreate, SavedQueryUpdate, SavedQueryOut, SavedQueryListItem,
)
from api.v1.services.query_engine.validators import validate_columns, validate_filters
from api.v1.services.query_engine.engine import execute_query
from api.v1.auth.permissions import RoleCode

router = APIRouter(prefix="/queries", tags=["Query Builder"])


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
    if user.institution_id and ds.institution_id and ds.institution_id != user.institution_id:
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
    if current_user.institution_id:
        query = query.filter(
            or_(
                DataSource.institution_id == current_user.institution_id,
                DataSource.institution_id.is_(None),
            )
        )
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

    rows, total = execute_query(client, ds, validated_cols, filters_dicts, body.offset, body.limit)

    columns_meta = [
        ColumnMeta(column_name=c.column_name, label=c.label, data_type=c.data_type.value)
        for c in validated_cols
    ]

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

    # Validar columnas y filtros si se actualizan
    if body.selected_columns is not None or body.filters is not None:
        ds = _get_user_datasource(sq.datasource_id, current_user, db)
        if body.selected_columns is not None:
            validate_columns(body.selected_columns, ds.columns_def)
        if body.filters is not None:
            filters_dicts = [f.model_dump() for f in body.filters]
            validate_filters(filters_dicts, ds.columns_def)

    # Aplicar cambios
    update_data = body.model_dump(exclude_unset=True)

    if "filters" in update_data:
        update_data["filters"] = [f.model_dump() for f in body.filters]

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

    rows, total = execute_query(client, ds, validated_cols, sq.filters or [], 0, 20)

    columns_meta = [
        ColumnMeta(column_name=c.column_name, label=c.label, data_type=c.data_type.value)
        for c in validated_cols
    ]

    return QueryExecuteResponse(
        items=rows, total=total, offset=0, limit=20, columns_meta=columns_meta,
    )
