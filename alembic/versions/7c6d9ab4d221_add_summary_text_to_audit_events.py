"""add summary text to audit events

Revision ID: 7c6d9ab4d221
Revises: 5d3d7f1c2a11
Create Date: 2026-03-23 13:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7c6d9ab4d221"
down_revision: Union[str, None] = "5d3d7f1c2a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("audit_events", sa.Column("summary_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("audit_events", "summary_text")
