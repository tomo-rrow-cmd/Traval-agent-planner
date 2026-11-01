"""make message sequence non-nullable

Revision ID: 20260710_04
Revises: 20260710_03
Create Date: 2026-07-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_04"
down_revision: Union[str, None] = "20260710_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "messages",
        "sequence",
        existing_type=sa.Integer(),
        nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "messages",
        "sequence",
        existing_type=sa.Integer(),
        nullable=True,
    )
