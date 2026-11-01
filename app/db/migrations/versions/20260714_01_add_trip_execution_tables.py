"""add trip execution tables — trip_states / checkins / expense_records / adjustments

迁移 ID: 20260714_01
父迁移: 20260710_04
创建时间: 2026-07-14

V2.0 行程执行 / 签到 / 花费 / 调整 相关表。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# 迁移标识
revision: str = "20260714_01"
down_revision: Union[str, None] = "20260710_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_table_if_missing(name: str, *columns) -> None:
    if name in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(name, *columns)


def _drop_table_if_exists(name: str) -> None:
    if name in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table(name)


def upgrade() -> None:
    # ==================== trip_states ====================
    _create_table_if_missing(
        "trip_states",
        sa.Column("plan_id", sa.String(36), sa.ForeignKey("plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("current_day", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("total_pois", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("checked_in", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("paused_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("last_lat", sa.Float(), nullable=True),
        sa.Column("last_lng", sa.Float(), nullable=True),
        sa.Column("budget_total", sa.Float(), nullable=True),
        sa.Column("budget_spent", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("budget_remain", sa.Float(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== checkins ====================
    _create_table_if_missing(
        "checkins",
        sa.Column("trip_id", sa.String(36), sa.ForeignKey("trip_states.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("poi_type", sa.String(20), nullable=False),
        sa.Column("poi_name", sa.String(200), nullable=False),
        sa.Column("poi_id", sa.String(36), nullable=True),
        sa.Column("source_day", sa.Integer(), nullable=True),
        sa.Column("lat", sa.Float(), nullable=True),
        sa.Column("lng", sa.Float(), nullable=True),
        sa.Column("photos", sa.JSON(), nullable=True, server_default="[]"),
        sa.Column("planned_at", sa.String(10), nullable=True),
        sa.Column("actual_at", sa.DateTime(), nullable=True),
        sa.Column("time_delta_min", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("planned_cost", sa.Float(), nullable=True),
        sa.Column("actual_cost", sa.Float(), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== expense_records ====================
    _create_table_if_missing(
        "expense_records",
        sa.Column("trip_id", sa.String(36), sa.ForeignKey("trip_states.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checkin_id", sa.String(36), sa.ForeignKey("checkins.id"), nullable=True),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("planned_amount", sa.Float(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("spent_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # ==================== adjustments ====================
    _create_table_if_missing(
        "adjustments",
        sa.Column("trip_id", sa.String(36), sa.ForeignKey("trip_states.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trigger_type", sa.String(30), nullable=False),
        sa.Column("trigger_detail", sa.JSON(), nullable=True),
        sa.Column("original_plan", sa.JSON(), nullable=True),
        sa.Column("adjusted_plan", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    _drop_table_if_exists("adjustments")
    _drop_table_if_exists("expense_records")
    _drop_table_if_exists("checkins")
    _drop_table_if_exists("trip_states")
