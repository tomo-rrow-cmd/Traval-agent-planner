"""业务服务层测试"""

from datetime import date, datetime
from types import SimpleNamespace

import pytest

from app.db.repositories.conversation_repo import ConversationRepository
from app.exceptions import BadRequestException, NotFoundException
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatSessionCreateRequest,
    ChatSessionUpdateRequest,
)
from app.schemas.plan import PlanDraftRequest
from app.schemas.user import UserPreferences, UserProfileUpdateRequest
import app.services.application.conversation_service as conversation_module
from app.services.application import ConversationService, TravelPlanService, UserService


class FakePlan:
    """用于服务层测试的方案对象"""

    def __init__(
        self,
        plan_id: str,
        user_id: str,
        destination: str = "北京",
        status: str = "generating",
    ):
        self.id = plan_id
        self.user_id = user_id
        self.destination = destination
        self.start_date = date(2026, 7, 10)
        self.end_date = date(2026, 7, 12)
        self.budget = 5000
        self.travelers = 1
        self.preferences = []
        self.status = status
        self.itinerary = []
        self.total_cost = None
        self.created_at = datetime(2026, 7, 7, 8, 0, 0)
        self.updated_at = datetime(2026, 7, 7, 8, 0, 0)
        # Attributes requried by _to_response / _to_summary
        self.departure = None
        self.travel_style = None
        self.version = 1
        self.is_favorite = False
        self.saved_at = None
        self.view_count = 0
        self.overview = None
        self.traffic_summary = {}
        self.food_summary = {}
        self.budget_detail = {}
        self.souvenir_recommendations = []
        self.weather_forecast = []
        self.packing_list = []
        self.tips = []
        self.avoid_list = []
        self.crowd_type = None
        self.full_data = {}
        self.hotel_plan = {}
        self.big_traffic = []
        self.meal_plan = []
        self.attraction_details = []
        self.food_details = []


class FakePlanRepository:
    """用于服务层测试的方案 Repository"""

    def __init__(self):
        self.plans: list[FakePlan] = []
        self.deleted: list[str] = []

    async def create_for_user(
        self,
        user_id: str,
        destination: str,
        start_date: date,
        end_date: date,
        budget: float,
        travelers: int = 1,
        preferences: list[str] | None = None,
        status: str = "generating",
    ) -> FakePlan:
        plan = FakePlan(
            plan_id="plan-1",
            user_id=user_id,
            destination=destination,
            status=status,
        )
        plan.start_date = start_date
        plan.end_date = end_date
        plan.budget = budget
        plan.travelers = travelers
        plan.preferences = preferences or []
        self.plans.append(plan)
        return plan

    async def get_by_id_for_user(self, plan_id: str, user_id: str) -> FakePlan | None:
        for plan in self.plans:
            if plan.id == plan_id and plan.user_id == user_id:
                return plan
        return None

    async def list_by_user(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
        status: str | None = None,
        saved_only: bool = False,
    ) -> list[FakePlan]:
        plans = [plan for plan in self.plans if plan.user_id == user_id]
        if status:
            plans = [plan for plan in plans if plan.status == status]
        if saved_only:
            plans = [plan for plan in plans if getattr(plan, "saved_at", None) is not None]
        return plans[offset:offset + limit]

    async def count_by_user(self, user_id: str, status: str | None = None, saved_only: bool = False) -> int:
        return len(await self.list_by_user(user_id=user_id, status=status, saved_only=saved_only))

    async def delete(self, entity: FakePlan, soft: bool = True) -> None:
        self.deleted.append(entity.id)


class FakeUser:
    """用于服务层测试的用户对象"""

    def __init__(self, user_id: str):
        self.id = user_id
        self.username = "tester"
        self.email = "tester@example.com"
        self.avatar = "https://example.com/avatar.png"
        self.preferences = {}
        self.created_at = datetime(2026, 7, 7, 8, 0, 0)


class FakeUserRepository:
    """用于服务层测试的用户 Repository"""

    def __init__(self, user: FakeUser | None = None):
        self.user = user
        self.saved_preferences: dict | None = None

    async def get_by_id(self, user_id: str) -> FakeUser | None:
        if self.user and self.user.id == user_id:
            return self.user
        return None

    async def update(self, user: FakeUser) -> FakeUser:
        self.user = user
        return user

    async def update_preferences(self, user: FakeUser, preferences: dict) -> FakeUser:
        user.preferences = preferences
        self.saved_preferences = preferences
        return user


class FakeConversation:
    """用于服务层测试的对话对象"""

    def __init__(self, session_id: str = "sess_mock_001", title: str = "测试会话"):
        self.id = session_id
        self.user_id = "user-1"
        self.title = title
        self.status = "active"
        self.pinned = False
        self.plan_id = None
        self.created_at = datetime(2026, 7, 7, 8, 0, 0)
        self.updated_at = datetime(2026, 7, 7, 8, 0, 0)


class FakeMessage:
    """用于服务层测试的消息对象"""

    def __init__(self, session_id: str, role: str, content: str):
        self.id = "msg_mock_001"
        self.session_id = session_id
        self.role = role
        self.content = content
        self.message_type = "text"
        self.metadata_json = {}
        self.created_at = datetime(2026, 7, 7, 8, 0, 0)


class FakeConversationRepository:
    """用于服务层测试的对话 Repository"""

    def __init__(self, db):
        self.db = db
        self.conversation = FakeConversation()

    async def create(self, user_id: str = "", title: str = "", destination: str = "", days: int = 0):
        _ = user_id, destination, days
        self.conversation.title = title or "新的旅行规划"
        return self.conversation

    async def get(self, conv_id: str, user_id: str | None = None):
        if conv_id != self.conversation.id and conv_id != "sess-1":
            return None
        if user_id and user_id != self.conversation.user_id:
            return None
        return self.conversation

    async def list_by_user(self, user_id: str = "", offset: int = 0, limit: int = 20):
        _ = user_id, offset, limit
        return [self.conversation], 1

    async def add_message(self, conv_id: str, role: str, content: str, **kwargs):
        _ = kwargs
        return FakeMessage(conv_id, role, content)

    async def get_messages_page(self, conv_id: str, page: int, page_size: int):
        _ = conv_id, page, page_size
        return [], 0

    async def get_plan_runs_by_ids(self, conv_id: str, run_ids: set[str]):
        _ = conv_id, run_ids
        return {}

    async def update_status(self, conv_id: str, status: str):
        _ = conv_id
        self.conversation.status = status

    async def reassign_user(self, source_user_id: str, target_user_id: str):
        _ = source_user_id, target_user_id
        return 2


class FakeAsyncSession:
    """用于服务层测试的异步 session 上下文"""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self):
        return None


@pytest.mark.asyncio
async def test_travel_plan_service_create_plan_returns_document_detail():
    repository = FakePlanRepository()
    service = TravelPlanService(repository)
    request = PlanDraftRequest(
        destination="北京",
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 12),
        budget=5000,
    )

    response = await service.create_plan("user-1", request)

    assert response.id == "plan-1"
    assert response.status == "generating"
    assert response.destination == "北京"
    assert response.days == 3
    assert response.total_budget == 5000


@pytest.mark.asyncio
async def test_travel_plan_service_get_plan_filters_by_user():
    repository = FakePlanRepository()
    repository.plans.append(FakePlan(plan_id="plan-1", user_id="user-1"))
    service = TravelPlanService(repository)

    response = await service.get_plan("user-1", "plan-1")

    assert response.id == "plan-1"


@pytest.mark.asyncio
async def test_travel_plan_service_get_plan_not_found_for_other_user():
    repository = FakePlanRepository()
    repository.plans.append(FakePlan(plan_id="plan-1", user_id="user-1"))
    service = TravelPlanService(repository)

    with pytest.raises(NotFoundException):
        await service.get_plan("user-2", "plan-1")


@pytest.mark.asyncio
async def test_travel_plan_service_list_plans_uses_document_pagination():
    repository = FakePlanRepository()
    repository.plans.append(FakePlan(plan_id="plan-1", user_id="user-1"))
    repository.plans.append(FakePlan(plan_id="plan-2", user_id="user-2"))
    service = TravelPlanService(repository)

    response = await service.list_plans("user-1", page=1, page_size=20)

    assert response.total == 1
    assert response.total_pages == 1
    assert [item.id for item in response.list] == ["plan-1"]


@pytest.mark.asyncio
async def test_travel_plan_service_delete_uses_repository():
    repository = FakePlanRepository()
    repository.plans.append(FakePlan(plan_id="plan-1", user_id="user-1"))
    service = TravelPlanService(repository)

    await service.delete_plan("user-1", "plan-1")

    assert repository.deleted == ["plan-1"]


@pytest.mark.asyncio
async def test_user_service_profile_and_preferences():
    repository = FakeUserRepository(FakeUser("user-1"))
    service = UserService(repository)
    preferences = UserPreferences(travel_style="relaxed", diet_preferences=["local_snacks"])

    profile = await service.get_profile("user-1")
    updated_profile = await service.update_profile(
        "user-1",
        UserProfileUpdateRequest(nickname="new-name", avatar_url="https://example.com/new.png"),
    )
    saved = await service.update_preferences("user-1", preferences)
    loaded = await service.get_preferences("user-1")

    assert profile.id == "user-1"
    assert profile.nickname == "tester"
    assert updated_profile.nickname == "new-name"
    assert saved.travel_style == "relaxed"
    assert loaded.diet_preferences == ["local_snacks"]
    assert repository.saved_preferences is not None


@pytest.mark.asyncio
async def test_conversation_service_returns_document_shapes(monkeypatch):
    monkeypatch.setattr(conversation_module, "ConversationRepository", FakeConversationRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())

    service = ConversationService()
    created = await service.create_session(
        "user-1",
        ChatSessionCreateRequest(title="测试会话"),
    )
    listed = await service.list_sessions("user-1")
    message, created_message = await service.record_message(
        "user-1",
        "sess-1",
        ChatMessageCreateRequest(content="你好"),
    )
    history = await service.get_messages("user-1", "sess-1")

    assert created.id == "sess_mock_001"
    assert created.title == "测试会话"
    assert listed.list[0].id == "sess_mock_001"
    assert message.session_id == "sess-1"
    assert created_message is True
    assert history.list == []


@pytest.mark.asyncio
async def test_list_sessions_derives_legacy_placeholder_title(monkeypatch):
    conversation = FakeConversation(title="新对话")

    class LegacyConversationRepository(FakeConversationRepository):
        async def list_by_user(self, user_id: str = "", offset: int = 0, limit: int = 20):
            _ = user_id, offset, limit
            return [(
                conversation,
                4,
                "好的，我现在开始生成完整旅行方案。",
                "  从武汉出发，想去北京玩三天  ",
            )], 1

    monkeypatch.setattr(conversation_module, "ConversationRepository", LegacyConversationRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())

    listed = await ConversationService().list_sessions("user-1")

    assert listed.list[0].title == "从武汉出发，想去北京玩三天"
    assert listed.list[0].last_message_preview == "好的，我现在开始生成完整旅行方案。"


@pytest.mark.asyncio
async def test_conversation_service_merges_anonymous_sessions(monkeypatch):
    monkeypatch.setattr(conversation_module, "ConversationRepository", FakeConversationRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())

    merged = await ConversationService().merge_sessions("anon:source", "user-1")

    assert merged == 2


@pytest.mark.asyncio
async def test_persist_plan_result_writes_run_and_message_in_one_commit(monkeypatch):
    run = SimpleNamespace(
        id="run-1", destination="杭州", days=2,
        summary={"destination": "杭州", "days": 2},
        created_at=datetime(2026, 7, 10, 8, 0, 0),
    )
    calls = []

    class AtomicRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            return FakeConversation(session_id=conv_id)

        async def create_plan_run(self, **kwargs):
            calls.append(("run", kwargs))
            return run

        async def update_status(self, *args, **kwargs):
            calls.append(("status", kwargs))

        async def add_message(self, *args, **kwargs):
            calls.append(("message", {"content": args[2], **kwargs}))
            return FakeMessage("sess-1", "assistant", args[2])

    session = FakeAsyncSession()
    session.commits = 0

    async def commit():
        session.commits += 1

    session.commit = commit
    monkeypatch.setattr(conversation_module, "ConversationRepository", AtomicRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: session)

    async def skip_plan_sync(self, **kwargs):
        _ = self, kwargs

    monkeypatch.setattr(ConversationService, "_sync_plan_record", skip_plan_sync)

    result = await ConversationService().persist_plan_result(
        "user-1", "sess-1", run.summary,
    )

    assert result.id == "run-1"
    assert [name for name, _ in calls] == ["run", "status", "message"]
    assert calls[-1][1]["metadata_json"]["plan_run_id"] == "run-1"
    assert calls[-1][1]["metadata_json"]["plan_id"] == "run-1"
    assert calls[-1][1]["metadata_json"]["result_format"] == "compact_v1"
    assert calls[-1][1]["client_message_id"] == "plan-result:run-1"
    assert "summary" in calls[-1][1]["metadata_json"]
    assert calls[-1][1]["content"] == "✅ 杭州2日方案已生成\n杭州 · 2天"
    assert session.commits == 1


@pytest.mark.asyncio
async def test_plan_table_sync_failure_keeps_core_result_committed(monkeypatch):
    run = SimpleNamespace(
        id="run-1", destination="杭州", days=2,
        summary={"destination": "杭州", "days": 2},
        created_at=datetime(2026, 7, 10, 8, 0, 0),
    )

    class CoreRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            return FakeConversation(session_id=conv_id)

        async def create_plan_run(self, **kwargs):
            _ = kwargs
            return run

        async def update_status(self, *args, **kwargs):
            _ = args, kwargs

        async def add_message(self, *args, **kwargs):
            _ = kwargs
            return FakeMessage("sess-1", "assistant", args[2])

    class CoreSession(FakeAsyncSession):
        def __init__(self):
            self.commits = 0

        async def commit(self):
            self.commits += 1

    class PlanSession(FakeAsyncSession):
        def __init__(self):
            self.commits = 0

        async def execute(self, *args, **kwargs):
            _ = args, kwargs
            return SimpleNamespace(scalar=lambda: 1)

        async def commit(self):
            self.commits += 1

    class FailingPlanRepository:
        def __init__(self, db):
            self.db = db

        async def upsert_plan_from_summary(self, **kwargs):
            _ = kwargs
            raise RuntimeError("plans write failed")

    core_session = CoreSession()
    plan_session = PlanSession()
    sessions = iter([core_session, plan_session])
    monkeypatch.setattr(conversation_module, "ConversationRepository", CoreRepository)
    monkeypatch.setattr(conversation_module, "PlanRepository", FailingPlanRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: next(sessions))

    result = await ConversationService().persist_plan_result(
        "user-1", "sess-1", run.summary,
    )

    assert result.id == "run-1"
    assert core_session.commits == 1
    assert plan_session.commits == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("failing_step", ["run", "status", "message"])
async def test_persist_plan_result_does_not_commit_partial_write(monkeypatch, failing_step):
    class FailingRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            return FakeConversation(session_id=conv_id)

        async def create_plan_run(self, **kwargs):
            if failing_step == "run":
                raise RuntimeError("run write failed")
            return SimpleNamespace(id="run-1")

        async def update_status(self, *args, **kwargs):
            if failing_step == "status":
                raise RuntimeError("status write failed")
            return None

        async def add_message(self, *args, **kwargs):
            if failing_step == "message":
                raise RuntimeError("message write failed")
            return FakeMessage("sess-1", "assistant", args[2])

    session = FakeAsyncSession()
    session.commits = 0

    async def commit():
        session.commits += 1

    session.commit = commit
    monkeypatch.setattr(conversation_module, "ConversationRepository", FailingRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: session)

    with pytest.raises(RuntimeError, match=f"{failing_step} write failed"):
        await ConversationService().persist_plan_result(
            "user-1", "sess-1", {"destination": "杭州", "days": 2},
        )

    assert session.commits == 0


@pytest.mark.asyncio
async def test_status_updates_never_overwrite_user_title(monkeypatch):
    conversation = FakeConversation(title="我的毕业旅行")
    db = SimpleNamespace()
    db.flush_calls = 0

    async def flush():
        db.flush_calls += 1

    db.flush = flush
    repo = ConversationRepository(db)

    async def get_conversation(conv_id, user_id=None):
        _ = conv_id, user_id
        return conversation

    monkeypatch.setattr(repo, "get", get_conversation)

    await repo.update_status(
        conversation.id,
        "completed",
        plan_id="run-1",
        destination="杭州",
        days=3,
        user_id="user-1",
    )
    await repo.update_status(conversation.id, "archived", user_id="user-1")

    assert conversation.title == "我的毕业旅行"
    assert conversation.status == "archived"
    assert conversation.plan_id == "run-1"
    assert conversation.destination == "杭州"
    assert conversation.days == 3
    assert db.flush_calls == 2


@pytest.mark.asyncio
async def test_message_history_hydrates_plan_summary_in_one_batch(monkeypatch):
    created_at = datetime(2026, 7, 10, 8, 30, 0)
    text_message = SimpleNamespace(
        id="msg-1", role="user", content="去杭州", message_type="text",
        metadata_json={}, created_at=created_at,
    )
    plan_message = SimpleNamespace(
        id="msg-2", role="assistant", content="# 杭州行程",
        message_type="plan_result", metadata_json={"plan_run_id": "run-1"},
        created_at=created_at,
    )
    batch_calls = []

    class HistoryRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            return FakeConversation(session_id=conv_id)

        async def get_messages_page(self, conv_id, page, page_size):
            return [text_message, plan_message], 2

        async def get_plan_runs_by_ids(self, conv_id, run_ids):
            batch_calls.append((conv_id, run_ids))
            return {"run-1": SimpleNamespace(summary={"destination": "杭州", "days": 2})}

    monkeypatch.setattr(conversation_module, "ConversationRepository", HistoryRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())

    history = await ConversationService().get_messages("user-1", "sess-1")

    assert [record.id for record in history.list] == ["msg-1", "msg-2"]
    assert history.list[1].created_at == created_at
    assert history.list[1].message_type == "plan_result"
    assert history.list[1].metadata == {
        "plan_run_id": "run-1",
        "summary": {"destination": "杭州", "days": 2},
    }
    assert plan_message.metadata_json == {"plan_run_id": "run-1"}
    assert batch_calls == [("sess-1", {"run-1"})]


@pytest.mark.asyncio
async def test_message_cursor_returns_direction_specific_next_id(monkeypatch):
    messages = [
        SimpleNamespace(
            id=f"msg-{index}", role="user", content=str(index), message_type="text",
            metadata_json={}, created_at=datetime(2026, 7, 10, 8, index, 0),
        )
        for index in range(1, 4)
    ]

    class CursorRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            return FakeConversation(session_id=conv_id)

        async def get_messages_cursor(self, conv_id, *, before_id, after_id, limit):
            return messages, True

        async def get_plan_runs_by_ids(self, conv_id, run_ids):
            return {}

    monkeypatch.setattr(conversation_module, "ConversationRepository", CursorRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())
    service = ConversationService()

    before = await service.get_messages("user-1", "sess-1", before_id="msg-4")
    after = await service.get_messages("user-1", "sess-1", after_id="msg-0")

    assert before.next_before_id == "msg-1"
    assert before.next_after_id is None
    assert after.next_before_id is None
    assert after.next_after_id == "msg-3"


@pytest.mark.asyncio
async def test_message_cursor_rejects_invalid_inputs(monkeypatch):
    class InvalidCursorRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            return FakeConversation(session_id=conv_id)

        async def get_messages_cursor(self, conv_id, *, before_id, after_id, limit):
            return None

    monkeypatch.setattr(conversation_module, "ConversationRepository", InvalidCursorRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())
    service = ConversationService()

    with pytest.raises(BadRequestException):
        await service.get_messages("user-1", "sess-1", before_id="missing")
    with pytest.raises(BadRequestException):
        await service.get_messages(
            "user-1", "sess-1", before_id="msg-1", after_id="msg-2",
        )
    with pytest.raises(BadRequestException):
        await service.get_messages("user-1", "sess-1", page=1, before_id="msg-1")


@pytest.mark.asyncio
async def test_conversation_operations_hide_other_users_sessions(monkeypatch):
    class OtherUsersRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            return None

    monkeypatch.setattr(conversation_module, "ConversationRepository", OtherUsersRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())
    service = ConversationService()

    operations = [
        service.get_messages("user-2", "sess-1"),
        service.update_session(
            "user-2", "sess-1", ChatSessionUpdateRequest(title="无权修改"),
        ),
        service.delete_session("user-2", "sess-1"),
        service.list_plan_runs("user-2", "sess-1"),
    ]
    for operation in operations:
        with pytest.raises(NotFoundException):
            await operation


@pytest.mark.asyncio
async def test_record_message_reuses_client_message_id(monkeypatch):
    conversation = FakeConversation(title="新的旅行规划")
    stored_message = None

    class IdempotentRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            return conversation

        async def add_message(self, conv_id, role, content, **kwargs):
            nonlocal stored_message
            if stored_message is not None:
                stored_message._idempotent_replay = True
                return stored_message
            stored_message = FakeMessage(conv_id, role, content)
            stored_message.message_type = "text"
            stored_message.metadata_json = {}
            stored_message._idempotent_replay = False
            return stored_message

    monkeypatch.setattr(conversation_module, "ConversationRepository", IdempotentRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())
    request = ChatMessageCreateRequest(content="杭州周末", client_message_id="client-1")
    service = ConversationService()

    first, first_created = await service.record_message("user-1", "sess-1", request)
    second, second_created = await service.record_message("user-1", "sess-1", request)

    assert first.id == second.id
    assert first_created is True
    assert second_created is False
    assert conversation.title == "杭州周末"


@pytest.mark.asyncio
async def test_record_message_replaces_legacy_placeholder_title(monkeypatch):
    conversation = FakeConversation(title="新对话")

    class LegacyTitleRepository:
        def __init__(self, db):
            self.db = db

        async def get(self, conv_id, user_id=None):
            _ = conv_id, user_id
            return conversation

        async def add_message(self, conv_id, role, content, **kwargs):
            _ = kwargs
            message = FakeMessage(conv_id, role, content)
            message._idempotent_replay = False
            return message

    monkeypatch.setattr(conversation_module, "ConversationRepository", LegacyTitleRepository)
    monkeypatch.setattr(conversation_module, "async_session_factory", lambda: FakeAsyncSession())

    await ConversationService().record_message(
        "user-1",
        "sess-1",
        ChatMessageCreateRequest(content="  武汉出发\n去北京玩三天  "),
    )

    assert conversation.title == "武汉出发 去北京玩三天"
