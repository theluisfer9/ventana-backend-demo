"""add user query checkpoints table

Revision ID: c1a2f7c9e5b4
Revises: b7b4921cf417
Create Date: 2026-03-13 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c1a2f7c9e5b4"
down_revision: Union[str, Sequence[str], None] = "b7b4921cf417"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_query_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("module", sa.String(length=100), nullable=False),
        sa.Column("scope", sa.String(length=100), nullable=False),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "module", "scope"),
    )
    op.create_index(
        op.f("ix_user_query_checkpoints_user_id"),
        "user_query_checkpoints",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_query_checkpoints_user_id"), table_name="user_query_checkpoints")
    op.drop_table("user_query_checkpoints")
