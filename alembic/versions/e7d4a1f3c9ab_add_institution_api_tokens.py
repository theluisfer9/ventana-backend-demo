"""add institution api tokens

Revision ID: e7d4a1f3c9ab
Revises: c1a2f7c9e5b4
Create Date: 2026-03-17 18:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e7d4a1f3c9ab"
down_revision: Union[str, None] = "c1a2f7c9e5b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "institution_api_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("institution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("token_prefix", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["institution_id"], ["institutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_institution_api_tokens_institution_id"), "institution_api_tokens", ["institution_id"], unique=False)
    op.create_index(op.f("ix_institution_api_tokens_token_prefix"), "institution_api_tokens", ["token_prefix"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_institution_api_tokens_token_prefix"), table_name="institution_api_tokens")
    op.drop_index(op.f("ix_institution_api_tokens_institution_id"), table_name="institution_api_tokens")
    op.drop_table("institution_api_tokens")
