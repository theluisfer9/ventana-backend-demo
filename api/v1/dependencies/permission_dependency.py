from typing import List, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status

from api.v1.models.user import User
from api.v1.dependencies.auth_dependency import get_current_user
from api.v1.auth.permissions import PermissionCode


class RequirePermission:
    """
    Dependency class to check if user has required permission(s).

    Usage:
        @router.get("/users")
        def get_users(
            current_user: User = Depends(RequirePermission(PermissionCode.USERS_READ))
        ):
            ...

        # Multiple permissions (all required)
        @router.post("/users")
        def create_user(
            current_user: User = Depends(
                RequirePermission([PermissionCode.USERS_CREATE, PermissionCode.USERS_READ])
            )
        ):
            ...
    """

    def __init__(
        self,
        permissions: PermissionCode | List[PermissionCode] | str | List[str],
        require_all: bool = True,
    ):
        """
        Args:
            permissions: Required permission(s)
            require_all: If True, all permissions are required. If False, any one is sufficient.
        """
        if isinstance(permissions, (PermissionCode, str)):
            self.permissions = [permissions]
        else:
            self.permissions = permissions
        self.require_all = require_all

    def __call__(self, current_user: User = Depends(get_current_user)) -> User:
        # Convert PermissionCode enums to strings
        required = [
            p.value if isinstance(p, PermissionCode) else p
            for p in self.permissions
        ]

        # Get user's permissions
        user_permissions = set()
        if current_user.role:
            user_permissions = {p.code for p in current_user.role.permissions}

        if self.require_all:
            # All permissions required
            has_permission = all(p in user_permissions for p in required)
        else:
            # Any permission is sufficient
            has_permission = any(p in user_permissions for p in required)

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para realizar esta acción",
            )

        return current_user


class RequireAnyPermission(RequirePermission):
    """
    Convenience class for requiring any one of multiple permissions.

    Usage:
        @router.get("/data")
        def get_data(
            current_user: User = Depends(
                RequireAnyPermission([PermissionCode.REPORTS_READ, PermissionCode.DATABASES_READ])
            )
        ):
            ...
    """

    def __init__(self, permissions: List[PermissionCode] | List[str]):
        super().__init__(permissions, require_all=False)


def require_permission(permission: PermissionCode | str):
    """
    Decorator to require a specific permission for a route.

    Usage:
        @router.get("/users")
        @require_permission(PermissionCode.USERS_READ)
        def get_users(current_user: User = Depends(get_current_user)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, current_user: User = Depends(get_current_user), **kwargs):
            perm_code = permission.value if isinstance(permission, PermissionCode) else permission

            user_permissions = set()
            if current_user.role:
                user_permissions = {p.code for p in current_user.role.permissions}

            if perm_code not in user_permissions:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tiene permisos para realizar esta acción",
                )

            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
