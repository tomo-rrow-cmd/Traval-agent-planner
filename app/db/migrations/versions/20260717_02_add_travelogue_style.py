"""add travelogue style

Revision ID: 20260717_02
Revises: 20260717_01
Create Date: 2026-07-17
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260717_02"
down_revision: Union[str, None] = "20260717_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    existing = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("travelogues")
    }
    if "style" not in existing:
        op.add_column(
            "travelogues",
            sa.Column("style", sa.String(length=20), nullable=False, server_default="diary"),
        )


def downgrade() -> None:
    existing = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns("travelogues")
    }
    if "style" in existing:
        op.drop_column("travelogues", "style")
