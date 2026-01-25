from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from api.v1.config.database import get_sync_db_pg
from api.v1.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleOut,
    RolePermissionsUpdate,
)
from api.v1.schemas.permission import PermissionOut
from api.v1.services.role import (
    get_role_by_id,
    get_role_by_code,
    get_all_roles,
    create_role,
    update_role,
    delete_role,
    update_role_permissions,
    get_all_permissions,
)
from api.v1.dependencies.permission_dependency import RequirePermission
from api.v1.auth.permissions import PermissionCode
from api.v1.models.user import User

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/", response_model=List[RoleOut])
def list_roles(
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """
    Listar todos los roles.
    Requiere permiso: roles:manage
    """
    return get_all_roles(db)


@router.post("/", response_model=RoleOut, status_code=status.HTTP_201_CREATED)
def create_new_role(
    role_data: RoleCreate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """
    Crear un nuevo rol.
    Requiere permiso: roles:manage
    """
    # Check if code already exists
    if get_role_by_code(db, role_data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un rol con este código",
        )

    new_role = create_role(db, role_data)
    return new_role


@router.get("/permissions", response_model=List[PermissionOut])
def list_permissions(
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """
    Listar todos los permisos disponibles.
    Requiere permiso: roles:manage
    """
    return get_all_permissions(db)


@router.get("/{role_id}", response_model=RoleOut)
def get_role(
    role_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """
    Obtener un rol por ID.
    Requiere permiso: roles:manage
    """
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )
    return role


@router.put("/{role_id}", response_model=RoleOut)
def update_existing_role(
    role_id: UUID,
    role_data: RoleUpdate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """
    Actualizar un rol.
    Requiere permiso: roles:manage
    """
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    # Check unique code if changed
    if role_data.code and role_data.code != role.code:
        if get_role_by_code(db, role_data.code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un rol con este código",
            )

    updated_role = update_role(db, role, role_data)
    return updated_role


@router.delete("/{role_id}")
def delete_existing_role(
    role_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """
    Eliminar un rol (solo roles no del sistema).
    Requiere permiso: roles:manage
    """
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se pueden eliminar roles del sistema",
        )

    delete_role(db, role)
    return {"message": "Rol eliminado correctamente"}


@router.put("/{role_id}/permissions", response_model=RoleOut)
def update_role_perms(
    role_id: UUID,
    permissions_data: RolePermissionsUpdate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """
    Actualizar permisos de un rol.
    Requiere permiso: roles:manage
    """
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado",
        )

    updated_role = update_role_permissions(db, role, permissions_data.permission_ids)
    return updated_role
