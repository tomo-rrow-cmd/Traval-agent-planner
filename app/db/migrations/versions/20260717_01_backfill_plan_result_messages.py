"""backfill missing plan result messages

Revision ID: 20260717_01
Revises: 20260715_01
Create Date: 2026-07-17
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json
from typing import Any, Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "20260717_01"
down_revision: Union[str, None] = "20260715_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PLAN_RESULT_FORMAT = "compact_v1"
BACKFILL_CLIENT_PREFIX = "plan-backfill:"


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _positive_int(value: Any) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def _positive_number(*values: Any) -> float | None:
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return None


def _format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _build_result_message(summary: dict[str, Any]) -> str:
    destination = _text(summary.get("destination"))
    origin = _text(summary.get("origin"))
    days = _positive_int(summary.get("days"))
    trip_config = _mapping(summary.get("trip_config"))
    travelers = _positive_int(
        trip_config.get("travelers")
        or summary.get("travelers")
        or summary.get("people_count")
    )

    if destination and days:
        title = f"{destination}{days}日方案"
    elif destination:
        title = f"{destination}旅行方案"
    else:
        title = "旅行方案"

    lines = [f"✅ {title}已生成"]
    route_parts = []
    if origin and destination:
        route_parts.append(f"{origin} → {destination}")
    elif destination:
        route_parts.append(destination)
    elif origin:
        route_parts.append(origin)
    if days:
        route_parts.append(f"{days}天")
    if travelers:
        route_parts.append(f"{travelers}人")
    if route_parts:
        lines.append(" · ".join(route_parts))

    budget = _mapping(summary.get("budget"))
    estimated = _positive_number(
        budget.get("actual_total"),
        summary.get("estimated_cost"),
    )
    total = _positive_number(
        budget.get("total_budget"),
        summary.get("total_budget"),
    )
    budget_parts = []
    if estimated is not None:
        budget_parts.append(f"预计 ¥{_format_number(estimated)}")
    if total is not None:
        budget_parts.append(f"预算 ¥{_format_number(total)}")
    if budget_parts:
        lines.append(" / ".join(budget_parts))
    return "\n".join(lines[:3])


def _legacy_summary(content: str) -> dict[str, Any]:
    if not content.startswith("__PLAN__:") or "|" not in content:
        return {}
    return _mapping(content.split("|", 1)[1])


def _fingerprint(summary: dict[str, Any]) -> tuple[str, ...]:
    return tuple(_text(summary.get(field)) for field in (
        "destination",
        "days",
        "origin",
        "start_date",
        "end_date",
    ))


def _created_at(row: dict[str, Any]) -> datetime:
    value = row.get("created_at")
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return datetime.min
    return datetime.min


def _find_missing_runs(
    runs: list[dict[str, Any]],
    messages: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    runs_by_id = {str(run["id"]): run for run in runs}
    covered: set[str] = set()
    unmatched_results: list[dict[str, Any]] = []

    for message in messages:
        metadata = _mapping(message.get("metadata_json"))
        run_id = _text(metadata.get("plan_run_id") or metadata.get("plan_id"))
        if run_id in runs_by_id:
            covered.add(run_id)
        else:
            unmatched_results.append(message)

    remaining = [run for run in runs if str(run["id"]) not in covered]
    for message in list(unmatched_results):
        metadata = _mapping(message.get("metadata_json"))
        result_summary = _mapping(metadata.get("summary"))
        if not result_summary:
            result_summary = _legacy_summary(_text(message.get("content")))
        if not result_summary:
            continue

        fingerprint = _fingerprint(result_summary)
        matches = [
            run for run in remaining
            if _fingerprint(_mapping(run.get("summary"))) == fingerprint
        ]
        if not matches:
            destination = _text(result_summary.get("destination"))
            days = _positive_int(result_summary.get("days"))
            matches = [
                run for run in remaining
                if _text(_mapping(run.get("summary")).get("destination") or run.get("destination")) == destination
                and _positive_int(_mapping(run.get("summary")).get("days") or run.get("days")) == days
            ]
        if matches:
            matched = min(
                matches,
                key=lambda run: abs((_created_at(run) - _created_at(message)).total_seconds()),
            )
            covered.add(str(matched["id"]))
            remaining.remove(matched)
            unmatched_results.remove(message)

    remaining.sort(key=lambda run: (_created_at(run), str(run["id"])))
    unmatched_results.sort(key=lambda message: (_created_at(message), str(message["id"])))
    for run, _message in zip(remaining, unmatched_results):
        covered.add(str(run["id"]))

    return [run for run in runs if str(run["id"]) not in covered]


def _resequence(connection: sa.Connection, conversation_id: str) -> None:
    connection.execute(sa.text("""
        WITH ranked AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at, id) AS new_sequence
            FROM messages
            WHERE conversation_id = :conversation_id
        )
        UPDATE messages AS target
        SET sequence = -ranked.new_sequence
        FROM ranked
        WHERE target.id = ranked.id
    """), {"conversation_id": conversation_id})
    connection.execute(sa.text("""
        UPDATE messages
        SET sequence = -sequence
        WHERE conversation_id = :conversation_id
    """), {"conversation_id": conversation_id})


def _backfill(connection: sa.Connection) -> int:
    run_rows = connection.execute(sa.text("""
        SELECT id, conversation_id, sequence, destination, days, summary,
               created_at, updated_at
        FROM conversation_plan_runs
        ORDER BY conversation_id, sequence, created_at, id
    """)).mappings().all()
    result_rows = connection.execute(sa.text("""
        SELECT id, conversation_id, content, message_type, metadata_json, created_at
        FROM messages
        WHERE message_type = 'plan_result' OR content LIKE '__PLAN__:%'
        ORDER BY conversation_id, created_at, id
    """)).mappings().all()

    runs_by_conversation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    messages_by_conversation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in run_rows:
        runs_by_conversation[str(row["conversation_id"])].append(dict(row))
    for row in result_rows:
        messages_by_conversation[str(row["conversation_id"])].append(dict(row))

    max_sequences = dict(connection.execute(sa.text("""
        SELECT conversation_id, COALESCE(MAX(sequence), 0)
        FROM messages
        GROUP BY conversation_id
    """)).all())
    message_table = sa.table(
        "messages",
        sa.column("id", sa.String(36)),
        sa.column("conversation_id", sa.String(36)),
        sa.column("role", sa.String(20)),
        sa.column("content", sa.Text()),
        sa.column("sequence", sa.Integer()),
        sa.column("message_type", sa.String(30)),
        sa.column("metadata_json", sa.JSON()),
        sa.column("client_message_id", sa.String(64)),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )

    inserts = []
    affected_conversations = set()
    for conversation_id, runs in runs_by_conversation.items():
        missing_runs = _find_missing_runs(
            runs,
            messages_by_conversation.get(conversation_id, []),
        )
        next_sequence = int(max_sequences.get(conversation_id, 0) or 0)
        for run in missing_runs:
            next_sequence += 1
            summary = _mapping(run.get("summary"))
            summary.setdefault("destination", _text(run.get("destination")))
            summary.setdefault("days", _positive_int(run.get("days")))
            created_at = _created_at(run)
            if created_at == datetime.min:
                created_at = datetime.utcnow()
            updated_at = _created_at({"created_at": run.get("updated_at")})
            if updated_at == datetime.min:
                updated_at = created_at
            inserts.append({
                "id": str(uuid.uuid4()),
                "conversation_id": conversation_id,
                "role": "assistant",
                "content": _build_result_message(summary),
                "sequence": next_sequence,
                "message_type": "plan_result",
                "metadata_json": {
                    "plan_run_id": str(run["id"]),
                    "plan_id": str(run["id"]),
                    "summary": summary,
                    "result_format": PLAN_RESULT_FORMAT,
                },
                "client_message_id": f"{BACKFILL_CLIENT_PREFIX}{run['id']}",
                "created_at": created_at,
                "updated_at": updated_at,
            })
            affected_conversations.add(conversation_id)

    if inserts:
        connection.execute(message_table.insert(), inserts)
        for conversation_id in sorted(affected_conversations):
            _resequence(connection, conversation_id)
    return len(inserts)


def upgrade() -> None:
    _backfill(op.get_bind())


def downgrade() -> None:
    connection = op.get_bind()
    affected = list(connection.execute(sa.text("""
        SELECT DISTINCT conversation_id
        FROM messages
        WHERE client_message_id LIKE :prefix
    """), {"prefix": f"{BACKFILL_CLIENT_PREFIX}%"}).scalars())
    connection.execute(sa.text("""
        DELETE FROM messages
        WHERE client_message_id LIKE :prefix
    """), {"prefix": f"{BACKFILL_CLIENT_PREFIX}%"})
    for conversation_id in affected:
        _resequence(connection, str(conversation_id))
