"""add message metadata and conversation pinned state

Revision ID: 20260710_02
Revises: 20260710_01
Create Date: 2026-07-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_02"
down_revision: Union[str, None] = "20260710_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "conversations",
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "messages",
        sa.Column("message_type", sa.String(length=30), nullable=False, server_default="text"),
    )
    op.add_column(
        "messages",
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("messages", "metadata_json")
    op.drop_column("messages", "message_type")
    op.drop_column("conversations", "pinned")
