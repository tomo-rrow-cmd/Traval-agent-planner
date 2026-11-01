"""PostgreSQL concurrency coverage for conversation ordering and idempotency."""

import asyncio
import importlib.util
from pathlib import Path
import uuid
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.models.conversation import Conversation, ConversationPlanRun, Message
from app.db.repositories.conversation_repo import ConversationRepository


pytestmark = pytest.mark.integration

MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "app/db/migrations/versions/20260717_01_backfill_plan_result_messages.py"
)
MIGRATION_SPEC = importlib.util.spec_from_file_location(
    "plan_result_backfill_integration",
    MIGRATION_PATH,
)
assert MIGRATION_SPEC and MIGRATION_SPEC.loader
plan_result_migration = importlib.util.module_from_spec(MIGRATION_SPEC)
MIGRATION_SPEC.loader.exec_module(plan_result_migration)


@pytest_asyncio.fixture
async def postgres_session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    database_url = settings.TEST_DATABASE_URL
    if not database_url:
        pytest.skip("TEST_DATABASE_URL is required for PostgreSQL concurrency tests")

    parsed = make_url(database_url)
    database_name = parsed.database or ""
    if not parsed.drivername.startswith("postgresql") or not database_name.endswith("_test"):
        pytest.fail(
            "TEST_DATABASE_URL must use PostgreSQL and a database name ending in '_test'",
            pytrace=False,
        )

    engine = create_async_engine(database_url, pool_size=10, max_overflow=10)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    try:
        async with engine.connect() as connection:
            revision = (await connection.execute(
                text("SELECT version_num FROM alembic_version")
            )).scalar_one_or_none()
        if revision != "20260717_01":
            pytest.fail(
                f"TEST_DATABASE_URL must be migrated to 20260717_01; found {revision!r}",
                pytrace=False,
            )
        yield session_factory
    finally:
        await engine.dispose()


@pytest_asyncio.fixture
async def conversation_id(
    postgres_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[str]:
    async with postgres_session_factory() as db:
        conversation = Conversation(
            user_id="integration-conversation-ordering",
            title="PostgreSQL concurrency test",
        )
        db.add(conversation)
        await db.commit()
        created_id = conversation.id

    try:
        yield created_id
    finally:
        async with postgres_session_factory() as db:
            await db.execute(delete(Message).where(Message.conversation_id == created_id))
            await db.execute(delete(ConversationPlanRun).where(
                ConversationPlanRun.conversation_id == created_id
            ))
            await db.execute(delete(Conversation).where(Conversation.id == created_id))
            await db.commit()


async def _add_message(
    session_factory: async_sessionmaker[AsyncSession],
    conversation_id: str,
    client_message_id: str,
) -> tuple[str, int, bool]:
    async with session_factory() as db:
        message = await ConversationRepository(db).add_message(
            conversation_id,
            "user",
            f"message:{client_message_id}",
            client_message_id=client_message_id,
        )
        replayed = bool(getattr(message, "_idempotent_replay", False))
        await db.commit()
        return message.id, message.sequence, replayed


async def _add_plan_run(
    session_factory: async_sessionmaker[AsyncSession],
    conversation_id: str,
    index: int,
) -> tuple[str, int]:
    async with session_factory() as db:
        run = await ConversationRepository(db).create_plan_run(
            conversation_id,
            destination="杭州",
            days=3,
            summary={"destination": "杭州", "days": 3, "index": index},
        )
        await db.commit()
        return run.id, run.sequence


@pytest.mark.asyncio
async def test_concurrent_duplicate_client_message_id_creates_one_message(
    postgres_session_factory: async_sessionmaker[AsyncSession],
    conversation_id: str,
):
    results = await asyncio.gather(*(
        _add_message(postgres_session_factory, conversation_id, "client-duplicate")
        for _ in range(8)
    ))

    async with postgres_session_factory() as db:
        count = (await db.execute(select(func.count(Message.id)).where(
            Message.conversation_id == conversation_id,
        ))).scalar_one()

    assert count == 1
    assert len({message_id for message_id, _, _ in results}) == 1
    assert [replayed for _, _, replayed in results].count(False) == 1
    assert [replayed for _, _, replayed in results].count(True) == 7


@pytest.mark.asyncio
async def test_concurrent_messages_receive_unique_contiguous_sequences(
    postgres_session_factory: async_sessionmaker[AsyncSession],
    conversation_id: str,
):
    results = await asyncio.gather(*(
        _add_message(postgres_session_factory, conversation_id, f"client-{index}")
        for index in range(12)
    ))

    async with postgres_session_factory() as db:
        stored_sequences = list((await db.execute(
            select(Message.sequence)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.sequence)
        )).scalars().all())

    assert len({message_id for message_id, _, _ in results}) == 12
    assert sorted(sequence for _, sequence, _ in results) == list(range(1, 13))
    assert stored_sequences == list(range(1, 13))
    assert all(sequence is not None for sequence in stored_sequences)


@pytest.mark.asyncio
async def test_concurrent_plan_runs_receive_unique_contiguous_sequences(
    postgres_session_factory: async_sessionmaker[AsyncSession],
    conversation_id: str,
):
    results = await asyncio.gather(*(
        _add_plan_run(postgres_session_factory, conversation_id, index)
        for index in range(12)
    ))

    async with postgres_session_factory() as db:
        stored_sequences = list((await db.execute(
            select(ConversationPlanRun.sequence)
            .where(ConversationPlanRun.conversation_id == conversation_id)
            .order_by(ConversationPlanRun.sequence)
        )).scalars().all())

    assert len({run_id for run_id, _ in results}) == 12
    assert sorted(sequence for _, sequence in results) == list(range(1, 13))
    assert stored_sequences == list(range(1, 13))
    assert all(sequence is not None for sequence in stored_sequences)


@pytest.mark.asyncio
async def test_reassign_user_moves_only_matching_conversations(
    postgres_session_factory: async_sessionmaker[AsyncSession],
):
    source_user_id = f"anon:{uuid.uuid4().hex[:31]}"
    target_user_id = str(uuid.uuid4())
    other_user_id = str(uuid.uuid4())
    conversation_ids: list[str] = []

    try:
        async with postgres_session_factory() as db:
            rows = [
                Conversation(user_id=source_user_id, title="匿名会话一"),
                Conversation(user_id=source_user_id, title="匿名会话二"),
                Conversation(user_id=other_user_id, title="其他会话"),
            ]
            db.add_all(rows)
            await db.commit()
            conversation_ids = [row.id for row in rows]

        async with postgres_session_factory() as db:
            merged = await ConversationRepository(db).reassign_user(
                source_user_id,
                target_user_id,
            )
            await db.commit()

        async with postgres_session_factory() as db:
            owners = dict((await db.execute(
                select(Conversation.id, Conversation.user_id).where(
                    Conversation.id.in_(conversation_ids)
                )
            )).all())

        assert merged == 2
        assert owners[conversation_ids[0]] == target_user_id
        assert owners[conversation_ids[1]] == target_user_id
        assert owners[conversation_ids[2]] == other_user_id
    finally:
        if conversation_ids:
            async with postgres_session_factory() as db:
                await db.execute(delete(Conversation).where(
                    Conversation.id.in_(conversation_ids)
                ))
                await db.commit()


@pytest.mark.asyncio
async def test_plan_result_backfill_inserts_only_missing_runs(
    postgres_session_factory: async_sessionmaker[AsyncSession],
):
    conversation_id = ""
    try:
        async with postgres_session_factory() as db:
            conversation = Conversation(
                user_id="integration-plan-result-backfill",
                title="Backfill test",
            )
            db.add(conversation)
            await db.commit()
            conversation_id = conversation.id

        async with postgres_session_factory() as db:
            repo = ConversationRepository(db)
            existing_run = await repo.create_plan_run(
                conversation_id,
                destination="北京",
                days=3,
                summary={"destination": "北京", "days": 3},
            )
            await repo.add_message(
                conversation_id,
                "assistant",
                "✅ 北京3日方案已生成",
                message_type="plan_result",
                metadata_json={"plan_run_id": existing_run.id},
            )
            missing_run = await repo.create_plan_run(
                conversation_id,
                destination="杭州",
                days=2,
                summary={"destination": "杭州", "days": 2},
            )
            await db.commit()

        async with postgres_session_factory() as db:
            connection = await db.connection()
            inserted = await connection.run_sync(plan_result_migration._backfill)
            inserted_again = await connection.run_sync(plan_result_migration._backfill)
            await db.commit()

        async with postgres_session_factory() as db:
            messages = list((await db.execute(
                select(Message)
                .where(
                    Message.conversation_id == conversation_id,
                    Message.message_type == "plan_result",
                )
                .order_by(Message.sequence)
            )).scalars().all())

        assert inserted == 1
        assert inserted_again == 0
        assert len(messages) == 2
        assert messages[1].metadata_json["plan_run_id"] == missing_run.id
        assert messages[1].metadata_json["result_format"] == "compact_v1"
        assert messages[1].content == "✅ 杭州2日方案已生成\n杭州 · 2天"
        assert [message.sequence for message in messages] == [1, 2]
    finally:
        if conversation_id:
            async with postgres_session_factory() as db:
                await db.execute(delete(Message).where(
                    Message.conversation_id == conversation_id
                ))
                await db.execute(delete(ConversationPlanRun).where(
                    ConversationPlanRun.conversation_id == conversation_id
                ))
                await db.execute(delete(Conversation).where(
                    Conversation.id == conversation_id
                ))
                await db.commit()
