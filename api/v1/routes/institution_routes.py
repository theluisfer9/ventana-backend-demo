from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from api.v1.config.database import get_sync_db_pg
from api.v1.schemas.institution import (
    InstitutionCreate,
    InstitutionUpdate,
    InstitutionOut,
)
from api.v1.services.institution import (
    get_institution_by_id,
    get_institution_by_code,
    get_all_institutions,
    create_institution,
    update_institution,
    delete_institution,
)
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.auth.permissions import PermissionCode
from api.v1.models.user import User

router = APIRouter(prefix="/institutions", tags=["Instituciones"])


@router.get("/", response_model=List[InstitutionOut])
def list_institutions(
    include_inactive: bool = False,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_READ)),
):
    """
    Listar todas las instituciones.
    Requiere permiso: users:read
    """
    return get_all_institutions(db, include_inactive=include_inactive)


@router.post("/", response_model=InstitutionOut, status_code=status.HTTP_201_CREATED)
def create_new_institution(
    institution_data: InstitutionCreate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_CREATE)),
):
    """
    Crear una nueva institución.
    Requiere permiso: users:create
    """
    # Check if code already exists
    if get_institution_by_code(db, institution_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe una institución con este código",
        )

    new_institution = create_institution(db, institution_data)
    return new_institution


@router.get("/{institution_id}", response_model=InstitutionOut)
def get_institution(
    institution_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_READ)),
):
    """
    Obtener una institución por ID.
    Requiere permiso: users:read
    """
    institution = get_institution_by_id(db, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institución no encontrada",
        )
    return institution


@router.put("/{institution_id}", response_model=InstitutionOut)
def update_existing_institution(
    institution_id: UUID,
    institution_data: InstitutionUpdate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_UPDATE)),
):
    """
    Actualizar una institución.
    Requiere permiso: users:update
    """
    institution = get_institution_by_id(db, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institución no encontrada",
        )

    # Check unique code if changed
    if institution_data.code and institution_data.code != institution.code:
        if get_institution_by_code(db, institution_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe una institución con este código",
            )

    updated_institution = update_institution(db, institution, institution_data)
    return updated_institution


@router.delete("/{institution_id}")
def delete_existing_institution(
    institution_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_DELETE)),
):
    """
    Desactivar una institución (soft delete).
    Requiere permiso: users:delete
    """
    institution = get_institution_by_id(db, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institución no encontrada",
        )

    delete_institution(db, institution, soft_delete=True)
    return {"message": "Institución desactivada correctamente"}
