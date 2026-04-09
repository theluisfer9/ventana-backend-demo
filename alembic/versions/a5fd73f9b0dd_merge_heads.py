"""merge heads

Revision ID: a5fd73f9b0dd
Revises: 7c6d9ab4d221, eb13391ba833
Create Date: 2026-03-24 12:02:07.641719

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5fd73f9b0dd'
down_revision: Union[str, Sequence[str], None] = ('7c6d9ab4d221', 'eb13391ba833')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
