"""Seed default roles and permissions

Revision ID: 002_seed_data
Revises: 001_users_auth
Create Date: 2026-01-25

"""
from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "002_seed_data"
down_revision: Union[str, None] = "001_users_auth"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Define UUIDs for consistency
PERMISSIONS = {
    # Users
    "users:read": {"name": "Ver usuarios", "module": "users"},
    "users:create": {"name": "Crear usuarios", "module": "users"},
    "users:update": {"name": "Editar usuarios", "module": "users"},
    "users:delete": {"name": "Eliminar usuarios", "module": "users"},
    # Roles
    "roles:manage": {"name": "Gestionar roles", "module": "roles"},
    # Beneficiaries
    "beneficiaries:read": {"name": "Consultar beneficiarios", "module": "beneficiaries"},
    "beneficiaries:export": {"name": "Exportar beneficiarios", "module": "beneficiaries"},
    # Databases
    "databases:read": {"name": "Ver integraciones", "module": "databases"},
    "databases:manage": {"name": "Gestionar integraciones", "module": "databases"},
    # Reports
    "reports:read": {"name": "Ver reportes", "module": "reports"},
    "reports:advanced": {"name": "Reportes avanzados", "module": "reports"},
    "reports:create": {"name": "Crear reportes", "module": "reports"},
    # System
    "system:config": {"name": "Configuración del sistema", "module": "system"},
    "system:monitor": {"name": "Monitoreo del sistema", "module": "system"},
    "system:audit": {"name": "Auditoría del sistema", "module": "system"},
}

ROLES = {
    "ADMIN": {
        "name": "Administrador del Sistema",
        "description": "Acceso completo al sistema - gestión de usuarios, configuración, monitoreo",
        "is_system": True,
        "permissions": list(PERMISSIONS.keys()),
    },
    "ANALYST": {
        "name": "Analista de Datos",
        "description": "Acceso a consultas y reportes completos, validación de integraciones",
        "is_system": True,
        "permissions": [
            "beneficiaries:read",
            "beneficiaries:export",
            "databases:read",
            "reports:read",
            "reports:advanced",
            "reports:create",
        ],
    },
    "INSTITUTIONAL": {
        "name": "Usuario Institucional",
        "description": "Consultas de beneficiarios, filtros básicos, exportaciones",
        "is_system": True,
        "permissions": [
            "beneficiaries:read",
            "beneficiaries:export",
            "reports:read",
        ],
    },
}

INSTITUTIONS = [
    {"code": "MIDES", "name": "Ministerio de Desarrollo Social"},
    {"code": "PNUD", "name": "Programa de las Naciones Unidas para el Desarrollo"},
    {"code": "MAGA", "name": "Ministerio de Agricultura, Ganadería y Alimentación"},
    {"code": "FODES", "name": "Fondo de Desarrollo Social"},
]


def upgrade() -> None:
    # Create permissions
    permissions_table = sa.table(
        "permissions",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("module", sa.String),
    )

    permission_ids = {}
    for code, data in PERMISSIONS.items():
        perm_id = uuid4()
        permission_ids[code] = perm_id
        op.execute(
            permissions_table.insert().values(
                id=perm_id,
                code=code,
                name=data["name"],
                description=f"Permiso para {data['name'].lower()}",
                module=data["module"],
            )
        )

    # Create roles
    roles_table = sa.table(
        "roles",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_system", sa.Boolean),
    )

    role_ids = {}
    for code, data in ROLES.items():
        role_id = uuid4()
        role_ids[code] = role_id
        op.execute(
            roles_table.insert().values(
                id=role_id,
                code=code,
                name=data["name"],
                description=data["description"],
                is_system=data["is_system"],
            )
        )

    # Create role_permissions
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("role_id", UUID(as_uuid=True)),
        sa.column("permission_id", UUID(as_uuid=True)),
    )

    for role_code, data in ROLES.items():
        role_id = role_ids[role_code]
        for perm_code in data["permissions"]:
            perm_id = permission_ids[perm_code]
            op.execute(
                role_permissions_table.insert().values(
                    role_id=role_id,
                    permission_id=perm_id,
                )
            )

    # Create institutions
    institutions_table = sa.table(
        "institutions",
        sa.column("id", UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
    )

    for inst in INSTITUTIONS:
        op.execute(
            institutions_table.insert().values(
                id=uuid4(),
                code=inst["code"],
                name=inst["name"],
                is_active=True,
            )
        )


def downgrade() -> None:
    # Delete in reverse order of dependencies
    op.execute("DELETE FROM role_permissions")
    op.execute("DELETE FROM roles WHERE is_system = true")
    op.execute("DELETE FROM permissions")
    op.execute("DELETE FROM institutions")
