from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from fastapi_pagination import Page, Params, create_page

from api.v1.config.database import get_sync_db_pg
from api.v1.schemas.user import (
    UserCreateByAdmin,
    UserUpdate,
    UserOut,
    UserFilters,
)
from api.v1.services.user import (
    get_user_by_id,
    get_user_by_email,
    get_user_by_username,
    create_user,
    update_user,
    delete_user,
    get_all_users,
    activate_user,
)
from api.v1.services.keycloak_admin import (
    create_keycloak_user,
    disable_keycloak_user,
    enable_keycloak_user,
    update_keycloak_user,
)
from api.v1.services.auth import revoke_all_user_sessions
from api.v1.dependencies.auth_dependency import get_current_user
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.dependencies.user_dependency import user_filters_dep
from api.v1.auth.permissions import PermissionCode
from api.v1.models.user import User

router = APIRouter(prefix="/users", tags=["Usuarios"])


@router.get("/", response_model=Page[UserOut])
def list_users(
    db: Session = Depends(get_sync_db_pg),
    params: Params = Depends(),
    filters: UserFilters = Depends(user_filters_dep),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_READ)),
):
    """
    Listar usuarios con paginación y filtros.
    Requiere permiso: users:read
    """
    offset = (params.page - 1) * params.size
    limit = params.size
    items, total = get_all_users(db, offset, limit, filters)
    return create_page(items, total=total, params=params)


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_new_user(
    user_data: UserCreateByAdmin,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_CREATE)),
):
    """
    Crear un nuevo usuario.
    Requiere permiso: users:create
    """
    # Check if email already exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este email",
        )

    # Check if username already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un usuario con este nombre de usuario",
        )

    keycloak_id = create_keycloak_user(
        email=user_data.email,
        username=user_data.username,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        temporary_password=user_data.password or "",
        enabled=user_data.is_active,
    )
    user_data.keycloak_id = keycloak_id
    new_user = create_user(db, user_data, created_by=current_user.id)
    return new_user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_READ)),
):
    """
    Obtener un usuario por ID.
    Requiere permiso: users:read
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_existing_user(
    user_id: UUID,
    user_data: UserUpdate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_UPDATE)),
):
    """
    Actualizar un usuario.
    Requiere permiso: users:update
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    # Check unique constraints if email/username changed
    if user_data.email and user_data.email != user.email:
        if get_user_by_email(db, user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con este email",
            )

    if user_data.username and user_data.username != user.username:
        if get_user_by_username(db, user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con este nombre de usuario",
            )

    if user.keycloak_id:
        update_keycloak_user(
            user.keycloak_id,
            email=user_data.email or user.email,
            username=user_data.username or user.username,
            first_name=user_data.first_name or user.first_name,
            last_name=user_data.last_name or user.last_name,
            enabled=user_data.is_active if user_data.is_active is not None else user.is_active,
        )
    updated_user = update_user(db, user, user_data)
    return updated_user


@router.delete("/{user_id}")
def delete_existing_user(
    user_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_DELETE)),
):
    """
    Desactivar un usuario (soft delete).
    Requiere permiso: users:delete
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    # Prevent self-deletion
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puede desactivar su propia cuenta",
        )

    if user.keycloak_id:
        disable_keycloak_user(user.keycloak_id)
    delete_user(db, user, soft_delete=True)

    # Revoke all user sessions
    revoke_all_user_sessions(db, str(user_id))

    return {"message": "Usuario desactivado correctamente"}


@router.put("/{user_id}/activate", response_model=UserOut)
def activate_existing_user(
    user_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_UPDATE)),
):
    """
    Activar un usuario desactivado.
    Requiere permiso: users:update
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    if user.keycloak_id:
        enable_keycloak_user(user.keycloak_id)
    activated_user = activate_user(db, user)
    return activated_user


@router.delete("/{user_id}/sessions")
def revoke_user_sessions(
    user_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.USERS_UPDATE)),
):
    """
    Revocar todas las sesiones de un usuario.
    Requiere permiso: users:update
    """
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    count = revoke_all_user_sessions(db, str(user_id))
    return {"message": f"{count} sesiones revocadas"}
