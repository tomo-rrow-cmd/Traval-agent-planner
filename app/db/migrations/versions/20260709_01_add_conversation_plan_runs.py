"""add conversation plan runs

迁移 ID: 20260709_01
父迁移: None
创建时间: 2026-07-09

数据库结构变更必须配套迁移脚本。
参考: .agent/conventions.md §2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# 迁移标识
revision: str = "20260709_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversation_plan_runs",
        sa.Column("conversation_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("destination", sa.String(length=100), nullable=True),
        sa.Column("days", sa.Integer(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_plan_runs_conversation_sequence",
        "conversation_plan_runs",
        ["conversation_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_plan_runs_conversation_sequence",
        table_name="conversation_plan_runs",
    )
    op.drop_table("conversation_plan_runs")
