from enum import Enum
from typing import List


class PermissionCode(str, Enum):
    """Enum of all permission codes in the system"""

    # Users
    USERS_READ = "users:read"
    USERS_CREATE = "users:create"
    USERS_UPDATE = "users:update"
    USERS_DELETE = "users:delete"

    # Roles
    ROLES_MANAGE = "roles:manage"

    # Beneficiaries
    BENEFICIARIES_READ = "beneficiaries:read"
    BENEFICIARIES_EXPORT = "beneficiaries:export"

    # Databases
    DATABASES_READ = "databases:read"
    DATABASES_MANAGE = "databases:manage"

    # Reports
    REPORTS_READ = "reports:read"
    REPORTS_ADVANCED = "reports:advanced"
    REPORTS_CREATE = "reports:create"

    # System
    SYSTEM_CONFIG = "system:config"
    SYSTEM_MONITOR = "system:monitor"
    SYSTEM_AUDIT = "system:audit"


class RoleCode(str, Enum):
    """Enum of system role codes"""
    ADMIN = "ADMIN"
    ANALYST = "ANALYST"
    INSTITUTIONAL = "INSTITUTIONAL"


# Default permissions for each role
ROLE_PERMISSIONS = {
    RoleCode.ADMIN: [
        PermissionCode.USERS_READ,
        PermissionCode.USERS_CREATE,
        PermissionCode.USERS_UPDATE,
        PermissionCode.USERS_DELETE,
        PermissionCode.ROLES_MANAGE,
        PermissionCode.BENEFICIARIES_READ,
        PermissionCode.BENEFICIARIES_EXPORT,
        PermissionCode.DATABASES_READ,
        PermissionCode.DATABASES_MANAGE,
        PermissionCode.REPORTS_READ,
        PermissionCode.REPORTS_ADVANCED,
        PermissionCode.REPORTS_CREATE,
        PermissionCode.SYSTEM_CONFIG,
        PermissionCode.SYSTEM_MONITOR,
        PermissionCode.SYSTEM_AUDIT,
    ],
    RoleCode.ANALYST: [
        PermissionCode.BENEFICIARIES_READ,
        PermissionCode.BENEFICIARIES_EXPORT,
        PermissionCode.DATABASES_READ,
        PermissionCode.REPORTS_READ,
        PermissionCode.REPORTS_ADVANCED,
        PermissionCode.REPORTS_CREATE,
    ],
    RoleCode.INSTITUTIONAL: [
        PermissionCode.BENEFICIARIES_READ,
        PermissionCode.BENEFICIARIES_EXPORT,
        PermissionCode.REPORTS_READ,
    ],
}


def get_permissions_for_role(role_code: str) -> List[str]:
    """
    Get the list of permission codes for a role.

    Args:
        role_code: The role code

    Returns:
        List of permission code strings
    """
    try:
        role = RoleCode(role_code)
        return [p.value for p in ROLE_PERMISSIONS.get(role, [])]
    except ValueError:
        return []
