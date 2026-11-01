from datetime import datetime, timedelta
import importlib.util
from pathlib import Path

import sqlalchemy as sa


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app/db/migrations/versions/20260717_01_backfill_plan_result_messages.py"
)
SPEC = importlib.util.spec_from_file_location("plan_result_backfill_migration", MIGRATION_PATH)
assert SPEC and SPEC.loader
migration = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(migration)


def _run(run_id: str, destination: str, days: int, created_at: datetime) -> dict:
    return {
        "id": run_id,
        "destination": destination,
        "days": days,
        "summary": {"destination": destination, "days": days},
        "created_at": created_at,
    }


def test_find_missing_runs_matches_new_and_legacy_results():
    started_at = datetime(2026, 7, 10, 8, 0, 0)
    runs = [
        _run("run-1", "北京", 3, started_at),
        _run("run-2", "杭州", 2, started_at + timedelta(hours=1)),
        _run("run-3", "成都", 4, started_at + timedelta(hours=2)),
    ]
    messages = [
        {
            "id": "msg-1",
            "content": "北京方案",
            "metadata_json": {"plan_run_id": "run-1"},
            "created_at": started_at,
        },
        {
            "id": "msg-2",
            "content": '__PLAN__:杭州之旅|{"destination":"杭州","days":2}',
            "metadata_json": {},
            "created_at": started_at + timedelta(hours=1),
        },
    ]

    missing = migration._find_missing_runs(runs, messages)

    assert [run["id"] for run in missing] == ["run-3"]


def test_find_missing_runs_pairs_unidentified_results_by_time():
    started_at = datetime(2026, 7, 10, 8, 0, 0)
    runs = [
        _run("run-1", "北京", 3, started_at),
        _run("run-2", "杭州", 2, started_at + timedelta(hours=1)),
    ]
    messages = [{
        "id": "msg-legacy",
        "content": "旧版方案结果",
        "metadata_json": {},
        "created_at": started_at,
    }]

    missing = migration._find_missing_runs(runs, messages)

    assert [run["id"] for run in missing] == ["run-2"]


def test_backfill_message_uses_compact_format():
    message = migration._build_result_message({
        "destination": "北京",
        "origin": "武汉",
        "days": 3,
        "travelers": 1,
        "budget": {"actual_total": 1349, "total_budget": 3000},
    })

    assert message == (
        "✅ 北京3日方案已生成\n"
        "武汉 → 北京 · 3天 · 1人\n"
        "预计 ¥1349 / 预算 ¥3000"
    )


def test_backfill_is_idempotent_and_resequences_messages():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    runs = sa.Table(
        "conversation_plan_runs",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36)),
        sa.Column("sequence", sa.Integer),
        sa.Column("destination", sa.String(100)),
        sa.Column("days", sa.Integer),
        sa.Column("summary", sa.JSON),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
    )
    messages = sa.Table(
        "messages",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36)),
        sa.Column("role", sa.String(20)),
        sa.Column("content", sa.Text),
        sa.Column("sequence", sa.Integer),
        sa.Column("message_type", sa.String(30)),
        sa.Column("metadata_json", sa.JSON),
        sa.Column("client_message_id", sa.String(64)),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
        sa.UniqueConstraint("conversation_id", "sequence"),
    )
    metadata.create_all(engine)
    started_at = datetime(2026, 7, 17, 8, 0, 0)

    with engine.begin() as connection:
        connection.execute(runs.insert(), [
            {
                "id": "run-1", "conversation_id": "conv-1", "sequence": 1,
                "destination": "北京", "days": 3,
                "summary": {"destination": "北京", "days": 3},
                "created_at": started_at, "updated_at": started_at,
            },
            {
                "id": "run-2", "conversation_id": "conv-1", "sequence": 2,
                "destination": "杭州", "days": 2,
                "summary": {"destination": "杭州", "days": 2},
                "created_at": started_at + timedelta(hours=1),
                "updated_at": started_at + timedelta(hours=1),
            },
        ])
        connection.execute(messages.insert(), {
            "id": "msg-1", "conversation_id": "conv-1", "role": "assistant",
            "content": "✅ 北京3日方案已生成", "sequence": 1,
            "message_type": "plan_result",
            "metadata_json": {"plan_run_id": "run-1"},
            "created_at": started_at, "updated_at": started_at,
        })

        assert migration._backfill(connection) == 1
        assert migration._backfill(connection) == 0
        result_messages = connection.execute(
            sa.select(messages).order_by(messages.c.sequence)
        ).mappings().all()

    assert [message["sequence"] for message in result_messages] == [1, 2]
    assert result_messages[1]["metadata_json"]["plan_run_id"] == "run-2"
    assert result_messages[1]["content"] == "✅ 杭州2日方案已生成\n杭州 · 2天"
