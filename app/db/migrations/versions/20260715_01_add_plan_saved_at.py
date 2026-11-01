"""add plan.saved_at column for "my plans" feature

Revision ID: 20260715_01
Revises: 20260714_02
Create Date: 2026-07-15
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_01"
down_revision: Union[str, None] = "20260714_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("plans")
    }
    if "saved_at" not in existing:
        op.add_column(
            "plans",
            sa.Column("saved_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    existing = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("plans")
    }
    if "saved_at" in existing:
        op.drop_column("plans", "saved_at")
