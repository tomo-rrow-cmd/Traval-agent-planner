"""add stable source identity to POI tables

Revision ID: 20260710_01
Revises: 20260709_01
Create Date: 2026-07-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_01"
down_revision: Union[str, None] = "20260709_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


POI_TABLES = ("attractions", "restaurants", "hotels")


def upgrade() -> None:
    for table_name in POI_TABLES:
        op.add_column(
            table_name,
            sa.Column(
                "source",
                sa.String(length=32),
                nullable=False,
                server_default="manual",
            ),
        )
        op.add_column(
            table_name,
            sa.Column("source_poi_id", sa.String(length=128), nullable=True),
        )
        op.create_unique_constraint(
            f"uq_{table_name}_source_poi_id",
            table_name,
            ["source", "source_poi_id"],
        )


def downgrade() -> None:
    for table_name in reversed(POI_TABLES):
        op.drop_constraint(
            f"uq_{table_name}_source_poi_id",
            table_name,
            type_="unique",
        )
        op.drop_column(table_name, "source_poi_id")
        op.drop_column(table_name, "source")
