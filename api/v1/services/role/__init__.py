from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from api.v1.models.role import Role
from api.v1.models.permission import Permission
from api.v1.schemas.role import RoleCreate, RoleUpdate


def get_role_by_id(db: Session, role_id: UUID) -> Optional[Role]:
    """Get a role by ID"""
    return db.get(Role, role_id)


def get_role_by_code(db: Session, code: str) -> Optional[Role]:
    """Get a role by code"""
    stmt = select(Role).where(Role.code == code)
    return db.execute(stmt).scalar_one_or_none()


def get_all_roles(db: Session) -> List[Role]:
    """Get all roles"""
    stmt = select(Role).order_by(Role.name)
    return list(db.execute(stmt).scalars().all())


def create_role(
    db: Session,
    role_data: RoleCreate,
) -> Role:
    """Create a new role"""
    data = role_data.model_dump(exclude={"permission_ids"})
    role = Role(**data)

    # Add permissions if provided
    if role_data.permission_ids:
        stmt = select(Permission).where(Permission.id.in_(role_data.permission_ids))
        permissions = list(db.execute(stmt).scalars().all())
        role.permissions = permissions

    db.add(role)
    db.commit()
    db.refresh(role)
    return role


def update_role(
    db: Session,
    role: Role,
    update_data: RoleUpdate,
) -> Role:
    """Update an existing role"""
    if role.is_system:
        # Only allow description updates for system roles
        if update_data.description is not None:
            role.description = update_data.description
    else:
        for key, value in update_data.model_dump(exclude_unset=True).items():
            setattr(role, key, value)

    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, role: Role) -> bool:
    """Delete a role (only non-system roles)"""
    if role.is_system:
        return False

    db.delete(role)
    db.commit()
    return True


def update_role_permissions(
    db: Session,
    role: Role,
    permission_ids: List[UUID],
) -> Role:
    """Update role permissions"""
    stmt = select(Permission).where(Permission.id.in_(permission_ids))
    permissions = list(db.execute(stmt).scalars().all())
    role.permissions = permissions
    db.commit()
    db.refresh(role)
    return role


def get_all_permissions(db: Session) -> List[Permission]:
    """Get all permissions"""
    stmt = select(Permission).order_by(Permission.module, Permission.code)
    return list(db.execute(stmt).scalars().all())
