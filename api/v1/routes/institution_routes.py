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
from api.v1.schemas.institution_api_token import (
    InstitutionApiTokenCreate,
    InstitutionApiTokenCreated,
    InstitutionApiTokenOut,
)
from api.v1.services.institution import (
    get_institution_by_id,
    get_institution_by_code,
    get_all_institutions,
    create_institution,
    update_institution,
    delete_institution,
)
from api.v1.services.institution_api_token import (
    generate_institution_api_token,
    list_institution_api_tokens,
    revoke_institution_api_token,
)
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.dependencies.auth_dependency import get_current_active_user
from api.v1.auth.permissions import PermissionCode
from api.v1.models.user import User
from api.v1.models.institution import Institution

router = APIRouter(prefix="/institutions", tags=["Instituciones"])


def _is_admin(user: User) -> bool:
    if not user.role:
        return False
    user_permissions = {p.code for p in user.role.permissions}
    return PermissionCode.SYSTEM_CONFIG.value in user_permissions


@router.get("/", response_model=List[InstitutionOut])
def list_institutions(
    include_inactive: bool = False,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(get_current_active_user),
):
    """
    Listar todas las instituciones.
    Admin: todas. Usuarios: solo su institución.
    """
    if _is_admin(current_user):
        return get_all_institutions(db, include_inactive=include_inactive)
    if current_user.institution_id:
        inst = db.query(Institution).filter(Institution.id == current_user.institution_id).first()
        return [inst] if inst else []
    return []


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
    current_user: User = Depends(get_current_active_user),
):
    """
    Obtener una institución por ID.
    Requiere: usuario autenticado
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


@router.get("/{institution_id}/api-tokens", response_model=List[InstitutionApiTokenOut])
def list_api_tokens(
    institution_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_READ)),
):
    institution = get_institution_by_id(db, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institución no encontrada",
        )
    return list_institution_api_tokens(db, institution_id)


@router.post("/{institution_id}/api-tokens", response_model=InstitutionApiTokenCreated, status_code=status.HTTP_201_CREATED)
def create_api_token(
    institution_id: UUID,
    token_data: InstitutionApiTokenCreate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_UPDATE)),
):
    institution = get_institution_by_id(db, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institución no encontrada",
        )
    api_token, plain_token = generate_institution_api_token(
        db,
        institution,
        token_data.name,
        token_data.expires_in_days,
    )
    return InstitutionApiTokenCreated(
        id=api_token.id,
        institution_id=api_token.institution_id,
        name=api_token.name,
        token_prefix=api_token.token_prefix,
        is_active=api_token.is_active,
        expires_at=api_token.expires_at,
        last_used_at=api_token.last_used_at,
        created_at=api_token.created_at,
        token=plain_token,
    )


@router.delete("/{institution_id}/api-tokens/{token_id}")
def revoke_api_token(
    institution_id: UUID,
    token_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_DELETE)),
):
    institution = get_institution_by_id(db, institution_id)
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Institución no encontrada",
        )
    if not revoke_institution_api_token(db, institution_id, token_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token institucional no encontrado",
        )
    return {"message": "Token institucional revocado correctamente"}
