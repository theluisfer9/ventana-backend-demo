"""drop legacy institution fields from datasource and saved query

Revision ID: c42b9d8e1173
Revises: 8f1b27e4a9c0
Create Date: 2026-03-25 16:10:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c42b9d8e1173"
down_revision: Union[str, Sequence[str], None] = "8f1b27e4a9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(inspector: sa.Inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _drop_foreign_key_for_column(inspector: sa.Inspector, table_name: str, column_name: str) -> None:
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key.get("name") and foreign_key.get("constrained_columns") == [column_name]:
            op.drop_constraint(foreign_key["name"], table_name, type_="foreignkey")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "data_sources", "institution_id"):
        _drop_foreign_key_for_column(inspector, "data_sources", "institution_id")
        op.drop_column("data_sources", "institution_id")

    if _has_column(inspector, "saved_queries", "institution_id"):
        _drop_foreign_key_for_column(inspector, "saved_queries", "institution_id")
        op.drop_column("saved_queries", "institution_id")

    if _has_column(inspector, "saved_queries", "is_shared"):
        op.drop_column("saved_queries", "is_shared")


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "data_sources", "institution_id"):
        op.add_column(
            "data_sources",
            sa.Column("institution_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            None,
            "data_sources",
            "institutions",
            ["institution_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _has_column(inspector, "saved_queries", "institution_id"):
        op.add_column(
            "saved_queries",
            sa.Column("institution_id", sa.UUID(), nullable=True),
        )
        op.create_foreign_key(
            None,
            "saved_queries",
            "institutions",
            ["institution_id"],
            ["id"],
            ondelete="SET NULL",
        )

    if not _has_column(inspector, "saved_queries", "is_shared"):
        op.add_column(
            "saved_queries",
            sa.Column("is_shared", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        )
