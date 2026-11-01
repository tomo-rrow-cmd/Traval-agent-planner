"""测试 FoodAgent.run() — mock 完整管线 + 异常路径"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agents.food_agent import FoodAgent
from tests.test_llm import MockLLM


@pytest.fixture
def mock_llm():
    return MockLLM(api_key="test", base_url="http://test", model="test")


@pytest.fixture
def agent(mock_llm):
    return FoodAgent(mock_llm)


@pytest.fixture
def sample_candidates():
    return [
        {"name": "餐厅A", "cuisine": "川菜", "rating": 4.5, "avg_price": 80,
         "tags": "麻辣", "relevance": 0.9, "rerank_score": 0.95},
        {"name": "餐厅B", "cuisine": "粤菜", "rating": 4.6, "avg_price": 120,
         "tags": "清淡", "relevance": 0.85, "rerank_score": 0.9},
        {"name": "餐厅C", "cuisine": "鲁菜", "rating": 4.3, "avg_price": 90,
         "tags": "海鲜", "relevance": 0.8},
        {"name": "餐厅D", "cuisine": "京菜", "rating": 4.4, "avg_price": 150,
         "tags": "烤鸭", "relevance": 0.75},
        {"name": "餐厅E", "cuisine": "湘菜", "rating": 4.2, "avg_price": 70,
         "tags": "辣味", "relevance": 0.7},
        {"name": "餐厅F", "cuisine": "本帮菜", "rating": 4.1, "avg_price": 110,
         "tags": "甜味", "relevance": 0.65},
    ]


@pytest.fixture
def seed_poi_stub(monkeypatch):
    process = MagicMock()
    process.communicate = AsyncMock(return_value=(b"", b""))
    create_subprocess = AsyncMock(return_value=process)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", create_subprocess)
    return create_subprocess


class TestFoodAgentRun:
    @pytest.mark.asyncio
    async def test_rag_search_preserves_coordinates(self, agent, monkeypatch):
        """RAG 候选坐标应直接进入餐饮计划，不依赖真实数据库补齐。"""
        rag_search = AsyncMock(return_value=[{
            "id": "restaurant-1",
            "name": "坐标餐厅",
            "latitude": 39.91,
            "longitude": 116.41,
            "address": "测试路1号",
            "source": "fixture",
            "source_poi_id": "poi-1",
        }])
        monkeypatch.setattr("app.agents.food_agent.rag_search", rag_search)

        result = await agent._rag_search("测试查询", "北京")

        assert result[0]["poi_id"] == "restaurant-1"
        assert result[0]["latitude"] == 39.91
        assert result[0]["longitude"] == 116.41
        assert result[0]["address"] == "测试路1号"

    @pytest.mark.asyncio
    async def test_run_with_rag_and_llm(self, agent, sample_candidates, monkeypatch):
        """完整管线：RAG 返回候选 → LLM 生成 meal_plan"""
        rag_search = AsyncMock(return_value=sample_candidates)
        monkeypatch.setattr(agent, "_rag_search", rag_search)

        # Mock _enrich_coords（避免 DB 调用）
        async def fake_enrich(self, meal_plan, city):
            pass
        monkeypatch.setattr(FoodAgent, "_enrich_coords", fake_enrich)

        # Mock _llm_plan 返回预设 meal plan
        async def fake_llm_plan(self, candidates, dest, days, prefs, budget, locs):
            return [
                {"day": 1, "meals": [
                    {"meal": "午餐", "restaurant": "餐厅A", "reason": "评分最高", "avg_price": 80},
                    {"meal": "晚餐", "restaurant": "餐厅B", "reason": "口碑好", "avg_price": 120},
                ]},
            ]

        monkeypatch.setattr(FoodAgent, "_llm_plan", fake_llm_plan)

        result = await agent.run({
            "destination": "北京",
            "days": 1,
            "cuisine_preferences": ["川菜", "粤菜"],
            "meal_budget": 150,
        })

        assert result["candidate_count"] == len(sample_candidates)
        assert len(result["meal_plan"]) == 1
        assert result["meal_plan"][0]["meals"][0]["restaurant"] == "餐厅A"
        rag_search.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_empty_candidates(self, agent, monkeypatch, seed_poi_stub):
        """自动拉取并再次搜索后仍为空 → 返回明确提示"""
        rag_search = AsyncMock(return_value=[])
        db_fallback = AsyncMock(return_value=[])
        monkeypatch.setattr(agent, "_rag_search", rag_search)
        monkeypatch.setattr(agent, "_db_fallback", db_fallback)

        result = await agent.run({
            "destination": "火星",
            "days": 1,
        })

        assert "message" in result
        assert "未找到" in result["message"]
        assert result["restaurants"] == []
        assert result["meal_plan"] == []
        assert rag_search.await_count == 2
        seed_poi_stub.assert_awaited_once_with(
            "python",
            "scripts/seed_poi.py",
            "--city",
            "火星",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        db_fallback.assert_awaited_once_with("火星")

    @pytest.mark.asyncio
    async def test_db_fallback_adds_candidates(
        self,
        agent,
        sample_candidates,
        monkeypatch,
        seed_poi_stub,
    ):
        """RAG 返回不足5个 → DB fallback 补充"""
        rag_search = AsyncMock(return_value=sample_candidates[:2])
        db_fallback = AsyncMock(return_value=[
            {"name": "DB餐厅", "cuisine": "家常菜", "rating": 4.0,
             "avg_price": 60, "latitude": 39.9, "longitude": 116.4,
             "tags": "", "relevance": 0.5, "address": "中关村"},
        ])

        async def fake_llm_plan(self, candidates, dest, days, prefs, budget, locs):
            return [{"day": 1, "meals": [{"meal": "午餐", "restaurant": "餐厅A", "reason": "test", "avg_price": 80}]}]

        async def fake_enrich(self, meal_plan, city):
            pass

        monkeypatch.setattr(agent, "_rag_search", rag_search)
        monkeypatch.setattr(agent, "_db_fallback", db_fallback)
        monkeypatch.setattr(FoodAgent, "_llm_plan", fake_llm_plan)
        monkeypatch.setattr(FoodAgent, "_enrich_coords", fake_enrich)

        result = await agent.run({
            "destination": "北京", "days": 1,
        })

        assert result["candidate_count"] == 3
        assert rag_search.await_count == 2
        seed_poi_stub.assert_awaited_once()
        db_fallback.assert_awaited_once_with("北京")

    @pytest.mark.asyncio
    async def test_enrich_coords_handles_db_empty(self, agent, sample_candidates, monkeypatch):
        """_enrich_coords 在 DB 为空时不崩溃"""
        rag_search = AsyncMock(return_value=sample_candidates)

        async def fake_llm_plan(self, candidates, dest, days, prefs, budget, locs):
            return [{"day": 1, "meals": [{"meal": "午餐", "restaurant": "餐厅A", "reason": "test", "avg_price": 80}]}]

        class FakeResult:
            def scalars(self):
                return self

            def all(self):
                return []

        class FakeSession:
            async def execute(self, stmt):
                return FakeResult()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

        monkeypatch.setattr(agent, "_rag_search", rag_search)
        monkeypatch.setattr(FoodAgent, "_llm_plan", fake_llm_plan)
        monkeypatch.setattr("app.db.session.async_session_factory", FakeSession)

        result = await agent.run({
            "destination": "北京", "days": 1, "meal_budget": 100,
        })

        assert result["meal_plan"][0]["meals"][0]["restaurant"] == "餐厅A"
        assert result["meal_plan"][0]["meals"][0]["latitude"] is None
        assert result["meal_plan"][0]["meals"][0]["longitude"] is None

    @pytest.mark.asyncio
    async def test_rag_search_handles_exception(
        self,
        agent,
        monkeypatch,
        seed_poi_stub,
    ):
        """异常路径: RAG 搜索抛异常时返回空列表不崩溃"""
        failing_rag = AsyncMock(side_effect=RuntimeError("RAG connection refused"))
        db_fallback = AsyncMock(return_value=[])
        monkeypatch.setattr("app.agents.food_agent.rag_search", failing_rag)
        monkeypatch.setattr(agent, "_db_fallback", db_fallback)

        result = await agent.run({"destination": "北京", "days": 1})
        assert "message" in result
        assert "未找到" in result["message"]
        assert failing_rag.await_count == 2
        seed_poi_stub.assert_awaited_once()
        db_fallback.assert_awaited_once_with("北京")

    @pytest.mark.asyncio
    async def test_llm_json_parse_fallback(self, agent, sample_candidates, monkeypatch):
        """异常路径: LLM 返回非法 JSON → _fallback_meals 回退"""
        rag_search = AsyncMock(return_value=sample_candidates)

        # Mock call_llm 返回非法 JSON → _llm_plan 的 json.loads 失败 → _fallback_meals
        async def fake_call_llm(self, messages, temperature=0.7, max_retries=3):
            return "这不是合法的JSON"  # 会触发 _llm_plan 内部的 json.loads 异常

        async def fake_enrich(self, meal_plan, city):
            pass

        monkeypatch.setattr(agent, "_rag_search", rag_search)
        monkeypatch.setattr(FoodAgent, "call_llm", fake_call_llm)
        monkeypatch.setattr(FoodAgent, "_enrich_coords", fake_enrich)

        # 不应该崩溃，应回退到 fallback
        result = await agent.run({
            "destination": "北京", "days": 2, "meal_budget": 100,
        })
        assert len(result["meal_plan"]) == 2  # fallback 按天分配


class TestFoodAgentConcurrency:
    """并发安全测试"""

    @pytest.mark.asyncio
    async def test_concurrent_runs_do_not_interfere(self, agent, monkeypatch):
        """并发运行多个 FoodAgent 实例，验证不会相互干扰"""
        candidates = [
            {"name": f"测试餐厅{i}", "cuisine": "川菜", "rating": 4.5,
             "avg_price": 80, "tags": "辣", "relevance": 0.9}
            for i in range(5)
        ]
        rag_search = AsyncMock(return_value=candidates)

        async def fake_llm(self, candidates, dest, days, prefs, budget, locs):
            return [{"day": 1, "meals": [
                {"meal": "午餐", "restaurant": f"{dest}餐厅", "reason": "test", "avg_price": 80},
            ]}]

        async def fake_enrich(self, meal_plan, city):
            pass

        monkeypatch.setattr(agent, "_rag_search", rag_search)
        monkeypatch.setattr(FoodAgent, "_llm_plan", fake_llm)
        monkeypatch.setattr(FoodAgent, "_enrich_coords", fake_enrich)

        # 3个并发 run
        tasks = [
            agent.run({"destination": "北京", "days": 1, "meal_budget": 100}),
            agent.run({"destination": "上海", "days": 1, "meal_budget": 80}),
            agent.run({"destination": "成都", "days": 1, "meal_budget": 60}),
        ]
        results = await asyncio.gather(*tasks)

        assert len(results) == 3
        for r in results:
            assert "meal_plan" in r
            assert len(r["meal_plan"]) == 1

    @pytest.mark.asyncio
    async def test_db_fallback_returns_restaurants(self, agent, monkeypatch):
        """_db_fallback: mock PostgreSQL 返回餐厅数据"""
        from unittest.mock import MagicMock

        mock_rest = MagicMock()
        mock_rest.name = "测试餐厅"
        mock_rest.cuisine = "川菜"
        mock_rest.rating = 4.5
        mock_rest.avg_price = 80
        mock_rest.latitude = 39.9
        mock_rest.longitude = 116.4
        mock_rest.address = "中关村"

        # Build a fake async session that doesn't use AsyncMock
        class FakeResult:
            def scalars(self):
                return self
            def all(self):
                return [mock_rest]

        class FakeSession:
            async def execute(self, stmt):
                return FakeResult()
            async def __aenter__(self):
                return self
            async def __aexit__(self, *a):
                pass

        monkeypatch.setattr("app.db.session.async_session_factory", FakeSession)

        result = await agent._db_fallback("北京")
        assert len(result) == 1
        assert result[0]["name"] == "测试餐厅"

    @pytest.mark.asyncio
    async def test_db_fallback_exception_returns_empty(self, agent, monkeypatch):
        """_db_fallback 异常路径 → 返回空列表"""
        def failing_factory():
            raise RuntimeError("DB connection refused")

        monkeypatch.setattr("app.db.session.async_session_factory", failing_factory)

        result = await agent._db_fallback("北京")
        assert result == []
