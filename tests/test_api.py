"""API 契约 MVP 测试"""

import asyncio
import json
from datetime import datetime
from types import SimpleNamespace

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.router import app
from app.api.v1 import chat as chat_module
from app.core.security import decode_access_token, decode_refresh_token
from app.dependencies import get_conversation_service, get_current_user, get_plan_service, get_user_service
from app.schemas.chat import (
    ChatMessageCreateRequest,
    ChatSession,
    ChatSessionCreateRequest,
    ConversationPlanRunRecord,
)
from app.schemas.common import PaginatedData
from app.schemas.plan import PlanFavoriteResult, PlanResponse, PlanShareRequest, PlanShareResult, PlanSummary
from app.schemas.user import UserPreferences, UserProfile, UserProfileUpdateRequest


def assert_streamed_agent_reply(events, expected_reply: str) -> None:
    event_names = [event for event, _ in events]
    assert event_names[0] == "step_start"
    assert event_names[-3:] == ["message", "step_end", "done"]

    deltas = [data for event, data in events if event == "message_delta"]
    assert "".join(delta["content_delta"] for delta in deltas) == expected_reply
    assert [delta["sequence"] for delta in deltas] == list(range(1, len(deltas) + 1))
    if len(expected_reply) > 8:
        assert len(deltas) > 1

    final_message = next(data for event, data in events if event == "message")
    assert final_message["content"] == expected_reply


@pytest_asyncio.fixture
async def client():
    """创建异步测试客户端"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class FakeConversationService:
    """用于 API 测试的对话服务"""

    async def create_session(self, user_id: str, request: ChatSessionCreateRequest) -> ChatSession:
        now = datetime(2026, 7, 7, 8, 0, 0)
        return ChatSession(
            id="sess-1",
            title=request.title or "新的旅行规划",
            status="active",
            message_count=0,
            created_at=now,
            updated_at=now,
        )

    async def list_sessions(self, user_id: str, page: int = 1, page_size: int = 20):
        now = datetime(2026, 7, 7, 8, 0, 0)
        return PaginatedData.create(
            [
                ChatSession(
                    id="sess-1",
                    title="测试会话",
                    status="active",
                    message_count=1,
                    created_at=now,
                    updated_at=now,
                )
            ],
            total=1,
            page=page,
            page_size=page_size,
        )

    async def delete_session(self, user_id: str, session_id: str) -> dict:
        return {}

    async def update_session(self, user_id: str, session_id: str, request) -> ChatSession:
        now = datetime(2026, 7, 7, 8, 0, 0)
        return ChatSession(
            id=session_id, title=request.title or "测试会话", status="active",
            pinned=bool(request.pinned), created_at=now, updated_at=now,
        )

    async def record_message(
        self,
        user_id: str,
        session_id: str,
        request: ChatMessageCreateRequest,
    ):
        return None, True

    async def get_messages(self, **kwargs):
        before_id = kwargs.get("before_id")
        after_id = kwargs.get("after_id")
        if before_id or after_id:
            return CursorPaginatedData(
                list=[], has_more=True,
                next_before_id="msg-before" if before_id else None,
                next_after_id="msg-after" if after_id else None,
            )
        return PaginatedData.create([], total=0, page=1, page_size=50)

    async def list_plan_runs(self, user_id: str, session_id: str):
        _ = user_id, session_id
        now = datetime(2026, 7, 7, 9, 0, 0)
        return [
            ConversationPlanRunRecord(
                id="run-2",
                destination="杭州",
                days=2,
                summary={"destination": "杭州", "days": 2},
                created_at=now,
            ),
            ConversationPlanRunRecord(
                id="run-1",
                destination="武汉",
                days=7,
                summary={"destination": "武汉", "days": 7},
                created_at=now,
            ),
        ]

    async def merge_sessions(self, source_user_id: str, target_user_id: str):
        _ = source_user_id, target_user_id
        return 2


class FakePlanService:
    """用于 API 测试的方案服务"""

    async def get_plan(self, user_id: str, plan_id: str) -> PlanResponse:
        return PlanResponse(id=plan_id, title="北京旅行方案", destination="北京", status="completed")

    async def list_plans(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        saved_only: bool = False,
    ):
        return PaginatedData.create(
            [
                PlanSummary(
                    id="plan-1",
                    title="北京旅行方案",
                    destination="北京",
                    status=status or "completed",
                    created_at=datetime(2026, 7, 7, 8, 0, 0),
                )
            ],
            total=1,
            page=page,
            page_size=page_size,
        )

    async def delete_plan(self, user_id: str, plan_id: str) -> dict:
        return {}

    async def share_plan(self, user_id: str, plan_id: str, request: PlanShareRequest) -> PlanShareResult:
        return PlanShareResult(share_url=f"https://travel.example.com/s/{plan_id}")

    async def toggle_favorite(self, user_id: str, plan_id: str) -> PlanFavoriteResult:
        return PlanFavoriteResult(is_favorite=True)


class FakeUserService:
    """用于 API 测试的用户服务"""

    async def get_profile(self, user_id: str) -> UserProfile:
        return UserProfile(id=user_id, nickname="tester")

    async def update_profile(self, user_id: str, request: UserProfileUpdateRequest) -> UserProfile:
        return UserProfile(id=user_id, nickname=request.nickname, avatar_url=request.avatar_url)

    async def get_preferences(self, user_id: str) -> UserPreferences:
        return UserPreferences()

    async def update_preferences(self, user_id: str, preferences: UserPreferences) -> UserPreferences:
        return preferences


@pytest_asyncio.fixture
async def authorized_client(monkeypatch):
    """创建覆盖鉴权和服务依赖的异步测试客户端"""

    async def override_current_user():
        return {"user_id": "user-1", "token": "test-token", "anonymous": False}

    async def override_conversation_service():
        return FakeConversationService()

    async def override_plan_service():
        return FakePlanService()

    async def override_user_service():
        return FakeUserService()

    async def fake_agent_sse_events(
        session_id: str,
        message: str,
        user_id: str,
        history: list[dict],
        service=None,
        images=None,
    ):
        _ = message, user_id, history, service, images
        yield ("message", {"role": "assistant", "content": "测试回复"})
        yield ("done", {"status": "completed", "session_id": session_id})

    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_conversation_service] = override_conversation_service
    app.dependency_overrides[get_plan_service] = override_plan_service
    app.dependency_overrides[get_user_service] = override_user_service
    monkeypatch.setattr(chat_module, "_agent_sse_events", fake_agent_sse_events)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def _chunk_text(chunk) -> str:
    return chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk


def _chat_analysis(mode="travel_planning", extracted=None, ambiguous_fields=None) -> str:
    data = {
        "mode": mode,
        "extracted": {
            "destination": "",
            "origin": "",
            "start_date": "",
            "end_date": "",
            "days": 0,
            "total_budget": 0,
            "reserve_budget": 0,
            "planning_budget": 0,
            "budget_no_limit": False,
            "preferences": [],
            "cuisine_preferences": [],
            "preferred_transport": "地铁",
            "preferences_provided": False,
            "pace": "适中",
            "hotel_star": 3,
            "hotel_budget": 500,
            "meal_budget": 100,
            "travelers": 1,
        },
        "ambiguous_fields": ambiguous_fields or [],
    }
    if extracted:
        data["extracted"].update(extracted)
    return json.dumps(data, ensure_ascii=False)


def _complete_trip_extracted() -> dict:
    return {
        "destination": "北京",
        "origin": "上海",
        "start_date": "2099-08-01",
        "end_date": "2099-08-03",
        "days": 3,
        "total_budget": 5000,
        "preferences": ["美食"],
        "preferences_provided": True,
    }


@pytest.mark.asyncio
async def test_sse_response_streams_complete_frames_with_headers():
    async def delayed_events():
        yield ("step_start", {"step": "chat"})
        await asyncio.sleep(0.05)
        yield ("done", {"status": "ok"})

    response = chat_module.sse_response(delayed_events(), keepalive=False)

    assert response.headers["cache-control"] == "no-cache, no-transform"
    assert response.headers["x-accel-buffering"] == "no"

    stream = response.body_iterator
    start = asyncio.get_running_loop().time()
    first = _chunk_text(await asyncio.wait_for(anext(stream), timeout=0.02))

    assert asyncio.get_running_loop().time() - start < 0.05
    assert first.startswith("id: evt_1\n")
    assert "event: step_start\n" in first
    assert 'data: {"step": "chat"}\n\n' in first

    second = _chunk_text(await asyncio.wait_for(anext(stream), timeout=0.2))
    assert "event: done\n" in second
    assert 'data: {"status": "ok"}\n\n' in second


@pytest.mark.asyncio
async def test_health_check_uses_v1_path(client: AsyncClient, monkeypatch):
    from app.api.v1 import ops as ops_module
    from app.services.vector.vector_store import VectorStoreHealth

    monkeypatch.setattr(
        ops_module.vector_store,
        "_health",
        VectorStoreHealth(status="healthy", collections={"attractions": 1}),
    )
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "healthy"
    assert body["data"]["dependencies"]["chroma"] == "healthy"
    assert "request_id" in body


@pytest.mark.asyncio
async def test_health_check_reports_empty_chroma_as_degraded(
    client: AsyncClient,
    monkeypatch,
):
    from app.api.v1 import ops as ops_module
    from app.services.vector.vector_store import VectorStoreHealth

    monkeypatch.setattr(
        ops_module.vector_store,
        "_health",
        VectorStoreHealth(status="empty"),
    )

    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "degraded"
    assert response.json()["data"]["dependencies"]["chroma"] == "empty"


@pytest.mark.asyncio
async def test_legacy_health_path_removed(client: AsyncClient):
    response = await client.get("/health")

    assert response.status_code == 404
    assert response.json()["code"] == 10003
    assert "request_id" in response.json()


@pytest.mark.asyncio
async def test_validation_errors_use_contract_response(client: AsyncClient):
    response = await client.post("/api/v1/auth/sms-codes", json={"phone": "123"})

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 10001
    assert body["data"] is None
    assert "request_id" in body


@pytest.mark.asyncio
async def test_new_paths_require_auth(client: AsyncClient):
    responses = [
        await client.get("/api/v1/chat/sessions"),
        await client.get("/api/v1/plans"),
        await client.get("/api/v1/user/profile"),
    ]

    for response in responses:
        assert response.status_code == 401
        assert response.json()["code"] == 20001


@pytest.mark.asyncio
async def test_old_contract_paths_removed(client: AsyncClient):
    responses = [
        await client.post("/api/v1/conversations", json={"message": "你好"}),
        await client.get("/api/v1/travel-plans"),
        await client.get("/api/v1/users/me"),
    ]

    assert [response.status_code for response in responses] == [404, 404, 404]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_auth_mock_contract(client: AsyncClient):
    sms = await client.post("/api/v1/auth/sms-codes", json={"phone": "13812345678"})
    login = await client.post(
        "/api/v1/auth/sessions",
        json={"method": "phone", "phone": "13812345678", "code": "123456"},
    )

    assert sms.status_code == 200
    assert sms.json()["data"]["retry_after"] == 60
    assert login.status_code == 200
    data = login.json()["data"]
    access_payload = decode_access_token(data["access_token"])
    refresh_payload = decode_refresh_token(data["refresh_token"])
    assert access_payload["type"] == "access"
    assert access_payload["sub"] == data["user"]["id"]
    assert access_payload["phone"] == "13812345678"
    assert refresh_payload["type"] == "refresh"
    assert refresh_payload["sub"] == data["user"]["id"]
    assert data["user"]["phone"] == "138****5678"


@pytest.mark.asyncio
async def test_create_chat_session_authorized(authorized_client: AsyncClient):
    response = await authorized_client.post(
        "/api/v1/chat/sessions",
        json={"title": "大理3日游规划"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["id"] == "sess-1"
    assert body["data"]["title"] == "大理3日游规划"


@pytest.mark.asyncio
async def test_list_sessions_uses_document_pagination(authorized_client: AsyncClient):
    response = await authorized_client.get("/api/v1/chat/sessions")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["total_pages"] == 1
    assert data["list"][0]["id"] == "sess-1"
    assert "items" not in data


@pytest.mark.asyncio
async def test_list_session_plans_returns_plan_runs(authorized_client: AsyncClient):
    response = await authorized_client.get("/api/v1/chat/sessions/sess-1/plans")

    assert response.status_code == 200
    data = response.json()["data"]
    assert [item["id"] for item in data] == ["run-2", "run-1"]
    assert data[0]["destination"] == "杭州"
    assert data[1]["summary"]["days"] == 7


@pytest.mark.asyncio
async def test_send_message_returns_sse(authorized_client: AsyncClient):
    response = await authorized_client.post(
        "/api/v1/chat/sessions/sess-1/messages",
        json={"content": "我想去大理玩3天"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message" in response.text
    assert "event: done" in response.text


@pytest.mark.asyncio
async def test_chat_pipeline_streams_agent_reply_and_waits_for_input(monkeypatch):
    class FakeLLM:
        async def chat(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            _ = messages, temperature, max_tokens, kwargs
            return _chat_analysis(extracted={
                "destination": "北京",
                "origin": "上海",
                "start_date": "2099-08-01",
                "end_date": "2099-08-03",
                "days": 3,
            })

        async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            yield await self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    class FakeConversationRecorder:
        def __init__(self):
            self.replies = []

        async def record_ai_reply(self, session_id: str, content: str, **kwargs):
            self.replies.append((session_id, content, kwargs.get("metadata")))

    from app.services.llm import deepseek as deepseek_module

    monkeypatch.setattr(deepseek_module, "DeepSeekLLM", FakeLLM)
    recorder = FakeConversationRecorder()

    events = [
        event
        async for event in chat_module._run_pipeline_events(
            "sess-1",
            "帮我规划：我从上海去北京玩3天",
            "user-1",
            [],
            service=recorder,
        )
    ]

    expected_reply = "这次总预算大概是多少，更偏爱自然风光、历史人文、美食，还是轻松慢游？"
    assert_streamed_agent_reply(events, expected_reply)
    assert events[-1][1]["status"] == "waiting_input"
    assert recorder.replies == [(
        "sess-1",
        expected_reply,
        {
            "agent_status": "collecting",
            "requested_fields": ["total_budget", "preferences"],
        },
    )]


@pytest.mark.asyncio
async def test_chat_pipeline_does_not_run_before_confirmation(monkeypatch):
    class FakeLLM:
        async def chat(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            _ = messages, temperature, max_tokens, kwargs
            return _chat_analysis(extracted=_complete_trip_extracted())

        async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            yield await self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    async def forbidden_pipeline(params):
        _ = params
        raise AssertionError("pipeline should wait for explicit confirmation")
        yield

    from app.orchestrator import pipeline as pipeline_module
    from app.services.llm import deepseek as deepseek_module

    monkeypatch.setattr(deepseek_module, "DeepSeekLLM", FakeLLM)
    monkeypatch.setattr(pipeline_module, "run_pipeline", forbidden_pipeline)

    events = [
        event
        async for event in chat_module._run_pipeline_events(
            "sess-1",
            "从上海出发去北京玩3天，预算5000，喜欢美食",
            "user-1",
            [],
        )
    ]

    expected_reply = next(data["content"] for evt, data in events if evt == "message")
    assert_streamed_agent_reply(events, expected_reply)
    assert events[-1][1]["status"] == "waiting_input"
    assert "确认后我再开始生成完整方案，可以吗？" in expected_reply


@pytest.mark.asyncio
async def test_chat_pipeline_runs_after_explicit_confirmation(monkeypatch):
    class FakeLLM:
        async def chat(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            _ = messages, temperature, max_tokens, kwargs
            return _chat_analysis(extracted=_complete_trip_extracted())

        async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            yield await self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    called = []

    async def fake_pipeline(params):
        called.append(params)
        yield ("done", {"summary": {"destination": params["destination"]}})

    from app.orchestrator import pipeline as pipeline_module
    from app.services.llm import deepseek as deepseek_module

    monkeypatch.setattr(deepseek_module, "DeepSeekLLM", FakeLLM)
    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_pipeline)

    confirmation = (
        "我理解的信息是：从 上海 出发，去 北京，日期 2099-08-01 至 2099-08-03，"
        "玩 3 天，预算 ¥5000，偏好 美食，菜系 无，交通 地铁。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    events = [
        event
        async for event in chat_module._run_pipeline_events(
            "sess-1",
            "确认，开始规划",
            "user-1",
            [
                {"role": "user", "content": "从上海出发去北京玩3天，预算5000，喜欢美食"},
                {"role": "assistant", "content": confirmation},
                {"role": "user", "content": "确认，开始规划"},
            ],
        )
    ]

    assert called and called[0]["destination"] == "北京"
    expected_reply = next(data["content"] for evt, data in events if evt == "message")
    assert_streamed_agent_reply(events, expected_reply)
    assert events[-1][1]["session_id"] == "sess-1"
    assert events[-1][1]["plan_id"] == "plan_sess-1"
    assert events[-1][1]["result_message"] == "✅ 北京旅行方案已生成\n北京"
    assert events[-1][1]["result_format"] == "compact_v1"
    assert events[-1][1]["summary"]["destination"] == "北京"


@pytest.mark.asyncio
async def test_chat_pipeline_persists_distinct_plan_runs_in_same_session(monkeypatch):
    class FakeLLM:
        async def chat(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            _ = temperature, max_tokens, kwargs
            content = messages[0]["content"]
            if "杭州" in content:
                    return _chat_analysis(extracted={
                        "destination": "杭州",
                        "origin": "上海",
                        "start_date": "2099-09-01",
                        "end_date": "2099-09-02",
                        "days": 2,
                    "total_budget": 3000,
                    "preferences": ["美食"],
                    "preferences_provided": True,
                })
            return _chat_analysis(extracted=_complete_trip_extracted())

        async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            yield await self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    async def fake_pipeline(params):
        yield ("done", {"summary": {
            "destination": params["destination"],
            "origin": params["origin"],
            "start_date": params["start_date"],
            "end_date": params["end_date"],
            "days": params["days"],
            "cuisine_preferences": params.get("cuisine_preferences", []),
            "preferred_transport": params.get("preferred_transport", "地铁"),
        }})

    class FakeConversationRuns:
        def __init__(self):
            self.runs = []
            self.replies = []

        async def get_session_context(self, user_id: str, session_id: str):
            _ = user_id, session_id
            return {
                "session_status": "completed" if self.runs else "active",
                "latest_plan_id": self.runs[-1].id if self.runs else "",
                "has_completed_plan": bool(self.runs),
                "plan_run_count": len(self.runs),
            }

        async def record_ai_reply(self, session_id: str, content: str, **kwargs):
            _ = kwargs
            self.replies.append((session_id, content))

        async def create_plan_run(self, session_id: str, summary: dict):
            _ = session_id
            run = SimpleNamespace(id=f"run-{len(self.runs) + 1}", summary=summary)
            self.runs.append(run)
            return run

    from app.orchestrator import pipeline as pipeline_module
    from app.services.llm import deepseek as deepseek_module

    monkeypatch.setattr(deepseek_module, "DeepSeekLLM", FakeLLM)
    monkeypatch.setattr(pipeline_module, "run_pipeline", fake_pipeline)

    first_confirmation = (
        "我理解的信息是：从 上海 出发，去 北京，日期 2099-08-01 至 2099-08-03，"
        "玩 3 天，预算 ¥5000，偏好 美食，菜系 无，交通 地铁。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    second_confirmation = (
        "我理解的信息是：从 上海 出发，去 杭州，日期 2099-09-01 至 2099-09-02，"
        "玩 2 天，预算 ¥3000，偏好 美食，菜系 无，交通 地铁。"
        "确认后我再开始生成完整方案，可以吗？"
    )
    service = FakeConversationRuns()

    first_events = [
        event
        async for event in chat_module._run_pipeline_events(
            "sess-1",
            "确认，开始规划",
            "user-1",
            [
                {"role": "user", "content": "从上海出发去北京玩3天，预算5000，喜欢美食"},
                {"role": "assistant", "content": first_confirmation},
                {"role": "user", "content": "确认，开始规划"},
            ],
            service=service,
        )
    ]
    second_events = [
        event
        async for event in chat_module._run_pipeline_events(
            "sess-1",
            "确认，开始规划",
            "user-1",
            [
                {"role": "user", "content": "从上海出发去北京玩3天，预算5000，喜欢美食"},
                {"role": "assistant", "content": first_confirmation},
                {"role": "user", "content": "确认，开始规划"},
                {"role": "assistant", "content": "好的，我现在开始生成完整旅行方案。"},
                {"role": "user", "content": "我还想再规划一个从上海去杭州玩2天，预算3000，喜欢美食"},
                {"role": "assistant", "content": second_confirmation},
                {"role": "user", "content": "确认，开始规划"},
            ],
            service=service,
        )
    ]

    assert first_events[-1][1]["plan_id"] == "run-1"
    assert second_events[-1][1]["plan_id"] == "run-2"
    assert [run.summary["destination"] for run in service.runs] == ["北京", "杭州"]
    assert service.runs[0].summary["start_date"] == "2099-08-01"
    assert service.runs[0].summary["end_date"] == "2099-08-03"
    assert service.runs[0].summary["cuisine_preferences"] == []
    assert service.runs[0].summary["preferred_transport"] == "地铁"


@pytest.mark.asyncio
async def test_chat_pipeline_daily_chat_does_not_run_pipeline(monkeypatch):
    class FakeLLM:
        async def chat(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            _ = temperature, max_tokens, kwargs
            first_content = messages[0]["content"]
            if "完整对话" in first_content:
                return _chat_analysis(mode="daily_chat")
            return "可以呀。以后需要规划旅行时，我也可以帮你整理出发地、目的地、天数、预算和偏好。"

        async def chat_stream(self, messages, temperature=0.7, max_tokens=4096, **kwargs):
            yield await self.chat(messages, temperature=temperature, max_tokens=max_tokens, **kwargs)

    async def forbidden_pipeline(params):
        _ = params
        raise AssertionError("daily chat should not run pipeline")
        yield

    from app.orchestrator import pipeline as pipeline_module
    from app.services.llm import deepseek as deepseek_module

    monkeypatch.setattr(deepseek_module, "DeepSeekLLM", FakeLLM)
    monkeypatch.setattr(pipeline_module, "run_pipeline", forbidden_pipeline)

    events = [
        event
        async for event in chat_module._run_pipeline_events(
            "sess-1",
            "帮我解释一下机器学习是什么",
            "user-1",
            [],
        )
    ]

    expected_reply = next(data["content"] for evt, data in events if evt == "message")
    assert_streamed_agent_reply(events, expected_reply)
    assert events[-1][1]["status"] == "waiting_input"
    assert "机器学习" in expected_reply or "旅行" in expected_reply


@pytest.mark.asyncio
async def test_run_pipeline_requires_confirmation(monkeypatch):
    from app.orchestrator import pipeline as pipeline_module

    class ForbiddenGraph:
        async def astream(self, initial, stream_mode=None):
            _ = initial, stream_mode
            raise AssertionError("unconfirmed planning must not run")
            yield

    monkeypatch.setattr(pipeline_module, "planner_graph", ForbiddenGraph())

    events = [
        event
        async for event in pipeline_module.run_pipeline({
            "destination": "北京",
            "origin": "上海",
            "start_date": "2099-08-01",
            "end_date": "2099-08-03",
            "days": 3,
            "total_budget": 5000,
            "preferences": [],
        })
    ]

    assert events == [(
        "done",
        {
            "status": "waiting_confirmation",
            "message": "confirmation_required",
        },
    )]


@pytest.mark.asyncio
async def test_run_pipeline_streams_langgraph_node_updates(monkeypatch):
    from app.orchestrator import pipeline as pipeline_module

    class FakeGraph:
        async def astream(self, initial, stream_mode=None):
            assert stream_mode == "updates"
            yield {
                "parallel_planning": {
                    "daily_plan": [],
                    "current_stage": "parallel_planning",
                }
            }
            yield {"decision": {"current_stage": "decision"}}
            yield {
                "budget": {
                    "current_stage": "completed",
                    "final_plan": {
                        "destination": initial["destination"],
                        "daily_itinerary": [{"day": 1, "attractions": []}],
                    },
                }
            }

    monkeypatch.setattr(pipeline_module, "planner_graph", FakeGraph())

    events = [
        event
        async for event in pipeline_module.run_pipeline({
            "destination": "北京",
            "origin": "上海",
            "start_date": "2099-08-01",
            "end_date": "2099-08-03",
            "days": 3,
            "total_budget": 5000,
            "preferences": [],
            "confirmed": True,
        })
    ]

    assert [evt for evt, _ in events] == [
        "step_start",
        "progress",
        "progress",
        "progress",
        "done",
    ]
    assert [data["step"] for evt, data in events if evt == "progress"] == [
        "parallel_planning",
        "decision",
        "completed",
    ]
    summary = events[-1][1]["summary"]
    assert summary["destination"] == "北京"
    assert summary["daily_itinerary"] == [{"day": 1, "attractions": []}]
    assert summary["daily_plan"] == [{"day": 1, "attractions": []}]


@pytest.mark.asyncio
async def test_create_plan_without_confirmation_waits(authorized_client: AsyncClient):
    response = await authorized_client.post("/api/v1/plans", json={"session_id": "sess-1"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: message" in response.text
    assert "waiting_confirmation" in response.text
    assert "event: step_start" not in response.text
    assert "redirect_url" not in response.text


@pytest.mark.asyncio
async def test_create_plan_confirmed_returns_sse(authorized_client: AsyncClient):
    response = await authorized_client.post(
        "/api/v1/plans",
        json={"session_id": "sess-1", "confirmed": True},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: step_start" in response.text
    assert "redirect_url" in response.text
    assert "plan_sess-1" in response.text


@pytest.mark.asyncio
async def test_regenerate_plan_requires_confirmation(authorized_client: AsyncClient):
    waiting = await authorized_client.post(
        "/api/v1/plans/plan-1/generations",
        json={"session_id": "sess-1"},
    )
    confirmed = await authorized_client.post(
        "/api/v1/plans/plan-1/generations",
        json={"session_id": "sess-1", "confirmed": True},
    )

    assert waiting.status_code == 200
    assert "waiting_confirmation" in waiting.text
    assert "event: step_start" not in waiting.text
    assert confirmed.status_code == 200
    assert "event: step_start" in confirmed.text
    assert "plan-1" in confirmed.text


@pytest.mark.asyncio
async def test_list_plans_authorized_uses_document_pagination(authorized_client: AsyncClient):
    response = await authorized_client.get("/api/v1/plans")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["total_pages"] == 1
    assert data["list"][0]["id"] == "plan-1"
    assert "items" not in data


@pytest.mark.asyncio
async def test_get_plan_authorized(authorized_client: AsyncClient):
    response = await authorized_client.get("/api/v1/plans/plan-1")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == "plan-1"
    assert data["destination"] == "北京"


@pytest.mark.asyncio
async def test_plan_modify_returns_sse(authorized_client: AsyncClient):
    response = await authorized_client.patch(
        "/api/v1/plans/plan-1",
        json={"modifications": [{"type": "add_constraint", "constraint": "轻松一点"}]},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: done" in response.text
    assert "updated_sections" in response.text


@pytest.mark.asyncio
async def test_export_format_error_uses_business_code(authorized_client: AsyncClient):
    response = await authorized_client.post("/api/v1/plans/plan-1/exports", params={"format": "zip"})

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == 40006
    assert body["data"] is None


@pytest.mark.asyncio
async def test_markdown_export_returns_file(authorized_client: AsyncClient):
    response = await authorized_client.post(
        "/api/v1/plans/plan-1/exports", params={"format": "md"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert response.content.startswith(b"# ")


def test_markdown_export_supports_structured_round_trip_traffic():
    from app.services.export.exporter import export_markdown

    content = export_markdown({
        "destination": "北京",
        "origin": "武汉",
        "days": 3,
        "budget": {},
        "big_traffic": {
            "trains": [{
                "trainCode": "G66", "departureTime": "07:30",
                "arrivalTime": "11:00", "duration": "03:30",
            }],
            "return_trains": [{
                "trainCode": "G67", "departureTime": "18:00",
                "arrivalTime": "21:30", "duration": "03:30",
            }],
        },
    })

    assert "### 去程" in content
    assert "G66" in content
    assert "### 返程" in content
    assert "G67" in content


@pytest.mark.asyncio
async def test_async_export_status_and_download(authorized_client: AsyncClient, monkeypatch):
    from app.services.export import task_manager as task_module

    task_module.export_task_manager.clear()
    monkeypatch.setattr(
        task_module, "export_plan",
        lambda plan, format: (b"%PDF-api-test", "application/pdf"),
    )
    created = await authorized_client.post(
        "/api/v1/plans/plan-1/exports", params={"format": "pdf"},
    )
    task_id = created.json()["data"]["task_id"]
    for _ in range(50):
        status = await authorized_client.get(f"/api/v1/tasks/{task_id}")
        if status.json()["data"]["status"] != "processing":
            break
        await asyncio.sleep(0.01)
    download = await authorized_client.get(f"/api/v1/tasks/{task_id}/download")

    assert created.status_code == 200
    assert status.json()["data"]["status"] == "completed"
    assert download.status_code == 200
    assert download.content.startswith(b"%PDF")
    task_module.export_task_manager.clear()


@pytest.mark.asyncio
async def test_user_profile_and_preferences_authorized(authorized_client: AsyncClient):
    profile = await authorized_client.get("/api/v1/user/profile")
    preferences = await authorized_client.put(
        "/api/v1/user/preferences",
        json={"travel_style": "relaxed", "diet_preferences": ["local_snacks"]},
    )

    assert profile.status_code == 200
    assert profile.json()["data"]["id"] == "user-1"
    assert profile.json()["data"]["nickname"] == "tester"
    assert preferences.status_code == 200
    assert preferences.json()["data"]["travel_style"] == "relaxed"
    assert preferences.json()["data"]["diet_preferences"] == ["local_snacks"]


@pytest.mark.asyncio
async def test_merge_anonymous_sessions_returns_session_count(authorized_client: AsyncClient):
    response = await authorized_client.post(
        "/api/v1/user/sessions/anonymous/merge",
        json={"anonymous_session_id": "sess_anonymous_test"},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {
        "merged_session_count": 2,
        "merged_plan_count": 0,
    }


@pytest.mark.asyncio
async def test_tasks_and_data_contract(authorized_client: AsyncClient):
    from app.services.export.task_manager import export_task_manager

    export_task = export_task_manager.create("user-1", "plan-1", "pdf")
    task = await authorized_client.get(f"/api/v1/tasks/{export_task.task_id}")
    cities = await authorized_client.get("/api/v1/data/cities", params={"keyword": "不存在"})
    weather = await authorized_client.get("/api/v1/data/weather", params={"city": "大理"})

    assert task.status_code == 200
    assert task.json()["data"]["status"] == "processing"
    assert cities.status_code == 200
    assert cities.json()["data"] == []
    assert weather.status_code == 200
    assert weather.json()["data"]["city"] == "大理"
    export_task_manager.clear()


@pytest.mark.asyncio
async def test_update_chat_session_contract(authorized_client: AsyncClient):
    response = await authorized_client.patch(
        "/api/v1/chat/sessions/sess-1", json={"title": "  杭州周末  ", "pinned": True},
    )

    assert response.status_code == 200
    assert response.json()["data"]["title"] == "杭州周末"
    assert response.json()["data"]["pinned"] is True


@pytest.mark.asyncio
async def test_update_chat_session_rejects_empty_body(authorized_client: AsyncClient):
    response = await authorized_client.patch("/api/v1/chat/sessions/sess-1", json={})

    assert response.status_code == 400
    assert response.json()["code"] == 10001
