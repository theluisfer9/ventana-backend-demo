"""add saved query roles

Revision ID: 8f1b27e4a9c0
Revises: 7c6d9ab4d221, f2c91b6e4d10
Create Date: 2026-03-25 12:30:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "8f1b27e4a9c0"
down_revision: Union[str, Sequence[str], None] = ("7c6d9ab4d221", "f2c91b6e4d10")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if inspector.has_table("saved_query_roles"):
        return

    op.create_table(
        "saved_query_roles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("saved_query_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["saved_query_id"], ["saved_queries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("saved_query_id", "role_id"),
    )


def downgrade() -> None:
    op.drop_table("saved_query_roles")
