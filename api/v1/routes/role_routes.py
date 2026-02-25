from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from api.v1.config.database import get_sync_db_pg
from api.v1.models.data_source import DataSource, RoleDataSource
from api.v1.models.role import Role
from api.v1.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleOut,
    RolePermissionsUpdate,
    RoleDataSourcesUpdate,
    RoleDataSourceOut,
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


# ── Role-DataSource assignment endpoints ──

@router.get("/{role_id}/datasources", response_model=list[RoleDataSourceOut])
def get_role_datasources(
    role_id: UUID,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """List datasources assigned to a role."""
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    assigned = (
        db.query(DataSource)
        .join(RoleDataSource, RoleDataSource.datasource_id == DataSource.id)
        .filter(RoleDataSource.role_id == role_id, DataSource.is_active.is_(True))
        .all()
    )
    return assigned


@router.put("/{role_id}/datasources", response_model=list[RoleDataSourceOut])
def update_role_datasources(
    role_id: UUID,
    body: RoleDataSourcesUpdate,
    db: Session = Depends(get_sync_db_pg),
    current_user: User = Depends(RequirePermission(PermissionCode.ROLES_MANAGE)),
):
    """Replace datasources assigned to a role."""
    role = get_role_by_id(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    unique_ids = set(body.datasource_ids)

    # Validate all datasource IDs exist and are active
    if unique_ids:
        valid_ds = (
            db.query(DataSource)
            .filter(DataSource.id.in_(unique_ids), DataSource.is_active.is_(True))
            .all()
        )
        valid_ids = {ds.id for ds in valid_ds}
        invalid = unique_ids - valid_ids
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Datasources no válidos o inactivos: {[str(i) for i in invalid]}",
            )

    # Delete existing assignments
    db.query(RoleDataSource).filter(RoleDataSource.role_id == role_id).delete()

    # Create new assignments
    for ds_id in unique_ids:
        db.add(RoleDataSource(role_id=role_id, datasource_id=ds_id))

    db.commit()

    # Return updated list
    assigned = (
        db.query(DataSource)
        .join(RoleDataSource, RoleDataSource.datasource_id == DataSource.id)
        .filter(RoleDataSource.role_id == role_id, DataSource.is_active.is_(True))
        .all()
    )
    return assigned
