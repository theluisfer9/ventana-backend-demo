"""add agrupar to saved_queries

Revision ID: 9d2b6a4f1c7e
Revises: c42b9d8e1173
Create Date: 2026-04-09 12:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision: str = "9d2b6a4f1c7e"
down_revision: Union[str, None] = "c42b9d8e1173"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _has_column("saved_queries", "agrupar"):
        op.add_column(
            "saved_queries",
            sa.Column(
                "agrupar",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("true"),
            ),
        )


def downgrade() -> None:
    if _has_column("saved_queries", "agrupar"):
        op.drop_column("saved_queries", "agrupar")
