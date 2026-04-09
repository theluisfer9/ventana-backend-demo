"""merge_heads

Revision ID: eb13391ba833
Revises: 65dfda30b3ed, f2c91b6e4d10
Create Date: 2026-03-18 00:03:49.190458

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb13391ba833'
down_revision: Union[str, Sequence[str], None] = ('65dfda30b3ed', 'f2c91b6e4d10')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
