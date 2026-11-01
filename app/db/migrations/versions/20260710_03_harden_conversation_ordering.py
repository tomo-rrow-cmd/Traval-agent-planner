"""harden conversation ordering and message idempotency

Revision ID: 20260710_03
Revises: 20260710_02
Create Date: 2026-07-10
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260710_03"
down_revision: Union[str, None] = "20260710_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _resequence(table: str) -> None:
    op.execute(sa.text(f"""
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (
                PARTITION BY conversation_id ORDER BY created_at, id
            ) AS new_sequence
            FROM {table}
        )
        UPDATE {table} AS target
        SET sequence = ranked.new_sequence
        FROM ranked
        WHERE target.id = ranked.id
    """))


def upgrade() -> None:
    op.add_column("messages", sa.Column("client_message_id", sa.String(64), nullable=True))
    _resequence("messages")
    _resequence("conversation_plan_runs")
    op.create_unique_constraint(
        "uq_messages_conversation_sequence", "messages", ["conversation_id", "sequence"],
    )
    op.create_unique_constraint(
        "uq_messages_conversation_client_message",
        "messages", ["conversation_id", "client_message_id"],
    )
    op.create_unique_constraint(
        "uq_conversation_plan_runs_conversation_sequence",
        "conversation_plan_runs", ["conversation_id", "sequence"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_conversation_plan_runs_conversation_sequence",
        "conversation_plan_runs", type_="unique",
    )
    op.drop_constraint(
        "uq_messages_conversation_client_message", "messages", type_="unique",
    )
    op.drop_constraint("uq_messages_conversation_sequence", "messages", type_="unique")
    op.drop_column("messages", "client_message_id")
