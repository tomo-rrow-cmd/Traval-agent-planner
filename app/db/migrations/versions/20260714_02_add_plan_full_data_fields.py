"""add plan full_data and rich detail columns

Revision ID: 20260714_02
Revises: 20260714_01
Create Date: 2026-07-14
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_02"
down_revision: Union[str, None] = "20260714_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_column_if_missing(table_name: str, column: sa.Column) -> None:
    existing = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns(table_name)
    }
    if column.name not in existing:
        op.add_column(table_name, column)


def _drop_column_if_exists(table_name: str, column_name: str) -> None:
    existing = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_columns(table_name)
    }
    if column_name in existing:
        op.drop_column(table_name, column_name)


def upgrade() -> None:
    # 新增标量字段
    _add_column_if_missing("plans", sa.Column("departure", sa.String(100), nullable=True))
    _add_column_if_missing("plans", sa.Column("crowd_type", sa.String(50), nullable=True))
    _add_column_if_missing("plans", sa.Column("travel_style", sa.String(50), nullable=True))
    _add_column_if_missing("plans", sa.Column("is_favorite", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column_if_missing("plans", sa.Column("view_count", sa.Integer(), nullable=False, server_default=sa.text("0")))
    _add_column_if_missing("plans", sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")))

    # 完整方案数据 JSON
    _add_column_if_missing("plans", sa.Column("full_data", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))

    # 各模块冗余 JSON 字段
    _add_column_if_missing("plans", sa.Column("overview", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column_if_missing("plans", sa.Column("traffic_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column_if_missing("plans", sa.Column("food_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column_if_missing("plans", sa.Column("budget_detail", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column_if_missing("plans", sa.Column("souvenir_recommendations", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    _add_column_if_missing("plans", sa.Column("weather_forecast", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    _add_column_if_missing("plans", sa.Column("packing_list", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    _add_column_if_missing("plans", sa.Column("tips", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    _add_column_if_missing("plans", sa.Column("avoid_list", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    _add_column_if_missing("plans", sa.Column("hotel_plan", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column_if_missing("plans", sa.Column("big_traffic", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    _add_column_if_missing("plans", sa.Column("meal_plan", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    _add_column_if_missing("plans", sa.Column("attraction_details", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))
    _add_column_if_missing("plans", sa.Column("food_details", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")))


def downgrade() -> None:
    for column_name in (
        "food_details", "attraction_details", "meal_plan", "big_traffic",
        "hotel_plan", "avoid_list", "tips", "packing_list",
        "weather_forecast", "souvenir_recommendations", "budget_detail",
        "food_summary", "traffic_summary", "overview", "full_data",
        "version", "view_count", "is_favorite", "travel_style",
        "crowd_type", "departure",
    ):
        _drop_column_if_exists("plans", column_name)
