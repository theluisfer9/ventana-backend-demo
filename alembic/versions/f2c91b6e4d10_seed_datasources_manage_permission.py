"""seed datasources manage permission

Revision ID: f2c91b6e4d10
Revises: e7d4a1f3c9ab
Create Date: 2026-03-17 20:05:00.000000
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa


revision: str = "f2c91b6e4d10"
down_revision: Union[str, None] = "e7d4a1f3c9ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
        INSERT INTO permissions (id, code, name, description, module)
        SELECT :perm_id, 'datasources:manage', 'Gestionar fuentes de datos',
               'Permiso para gestionar fuentes de datos', 'datasources'
        WHERE NOT EXISTS (
            SELECT 1 FROM permissions WHERE code = 'datasources:manage'
        )
        """
        ).bindparams(perm_id=str(uuid4()))
    )

    op.execute(
        """
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT r.id, p.id
        FROM roles r
        JOIN permissions p ON p.code = 'datasources:manage'
        WHERE r.code = 'ADMIN'
          AND NOT EXISTS (
              SELECT 1
              FROM role_permissions rp
              WHERE rp.role_id = r.id
                AND rp.permission_id = p.id
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE code = 'datasources:manage'
        )
        """
    )
    op.execute("DELETE FROM permissions WHERE code = 'datasources:manage'")
