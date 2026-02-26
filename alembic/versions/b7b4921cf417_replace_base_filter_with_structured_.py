"""replace base_filter with structured columns

Revision ID: b7b4921cf417
Revises: 604001d39dc6
Create Date: 2026-02-25 19:06:15.879233

"""
from typing import Sequence, Union
import json
import re

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7b4921cf417'
down_revision: Union[str, Sequence[str], None] = '604001d39dc6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _parse_base_filter(bf: str) -> tuple[list[str], str]:
    """Parse a raw base_filter string into (columns, logic)."""
    bf = bf.strip()
    if bf.startswith("(") and bf.endswith(")"):
        bf = bf[1:-1].strip()
    logic = "OR" if " OR " in bf.upper() else "AND"
    parts = re.split(r"\s+(?:OR|AND)\s+", bf, flags=re.IGNORECASE)
    columns = []
    for part in parts:
        part = part.strip()
        match = re.match(r"^(\w+)\s*=\s*1$", part)
        if match:
            columns.append(match.group(1))
    return columns, logic


def upgrade() -> None:
    # 1. Add new columns
    op.add_column('data_sources', sa.Column('base_filter_columns', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'))
    op.add_column('data_sources', sa.Column('base_filter_logic', sa.String(3), nullable=False, server_default='OR'))

    # 2. Data migration: parse existing base_filter values
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, base_filter FROM data_sources WHERE base_filter IS NOT NULL AND base_filter != ''"))
    for row in rows:
        ds_id, bf = row[0], row[1]
        columns, logic = _parse_base_filter(bf)
        conn.execute(
            sa.text("UPDATE data_sources SET base_filter_columns = :cols, base_filter_logic = :logic WHERE id = :id"),
            {"cols": json.dumps(columns), "logic": logic, "id": ds_id},
        )

    # 3. Drop old column
    op.drop_column('data_sources', 'base_filter')


def downgrade() -> None:
    # 1. Re-add old column
    op.add_column('data_sources', sa.Column('base_filter', sa.Text(), nullable=True))

    # 2. Best-effort reverse: reconstruct raw SQL from structured data
    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, base_filter_columns, base_filter_logic FROM data_sources"))
    for row in rows:
        ds_id = row[0]
        cols = row[1] if row[1] else []
        logic = row[2] if row[2] else "OR"
        if cols:
            parts = [f"{c} = 1" for c in cols]
            if len(parts) == 1:
                bf = parts[0]
            else:
                bf = f"({f' {logic} '.join(parts)})"
            conn.execute(
                sa.text("UPDATE data_sources SET base_filter = :bf WHERE id = :id"),
                {"bf": bf, "id": ds_id},
            )

    # 3. Drop new columns
    op.drop_column('data_sources', 'base_filter_logic')
    op.drop_column('data_sources', 'base_filter_columns')
