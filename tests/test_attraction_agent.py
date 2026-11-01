"""测试 app/agents/attraction_agent.py — AttractionAgent"""

import pytest
from unittest.mock import AsyncMock
from app.agents.attraction_agent import AttractionAgent, _rank_score, _name_key
from tests.test_llm import MockLLM


@pytest.fixture
def mock_llm():
    return MockLLM(api_key="test", base_url="http://test", model="test")


@pytest.fixture
def agent(mock_llm):
    return AttractionAgent(mock_llm)


@pytest.fixture
def sample_candidates():
    return [
        {"name": "故宫", "rating": 4.8, "price": 60, "latitude": 39.916, "longitude": 116.397,
         "tags": "历史;文化;博物馆", "rerank_score": 0.95, "address": "东城区",
         "poi_id": "p1", "source": "rag", "source_poi_id": "s1", "category": "博物馆"},
        {"name": "长城", "rating": 4.9, "price": 45, "latitude": 40.431, "longitude": 116.570,
         "tags": "户外;登山;世界遗产", "rerank_score": 0.92, "address": "延庆区",
         "poi_id": "p2", "source": "rag", "source_poi_id": "s2", "category": "自然风光"},
        {"name": "天坛", "rating": 4.6, "price": 35, "latitude": 39.882, "longitude": 116.406,
         "tags": "历史;古建筑;园林", "rerank_score": 0.88, "address": "东城区",
         "poi_id": "p3", "source": "rag", "source_poi_id": "s3", "category": "古建筑"},
        {"name": "颐和园", "rating": 4.7, "price": 30, "latitude": 39.999, "longitude": 116.275,
         "tags": "园林;湖泊;自然风光", "rerank_score": 0.90, "address": "海淀区",
         "poi_id": "p4", "source": "rag", "source_poi_id": "s4", "category": "园林"},
        {"name": "鸟巢", "rating": 4.4, "price": 50, "latitude": 39.992, "longitude": 116.390,
         "tags": "现代建筑;体育", "relevance": 0.85, "address": "朝阳区",
         "poi_id": "p5", "source": "rag", "source_poi_id": "s5", "category": "现代建筑"},
    ]


# ═══════════════════════════════════════════════════════
# 纯函数
# ═══════════════════════════════════════════════════════

class TestRankScore:
    def test_rerank_score_priority(self):
        assert _rank_score({"rerank_score": 0.9, "relevance": 0.5}) == 0.9

    def test_fallback_to_relevance(self):
        assert _rank_score({"relevance": 0.6}) == 0.6

    def test_default_zero(self):
        assert _rank_score({}) == 0


class TestNameKey:
    def test_normalize(self):
        assert _name_key("故宫（紫禁城）") == "故宫"
        assert _name_key("  Great Wall  ") == "greatwall"


# ═══════════════════════════════════════════════════════
# _parse_plan（纯同步）
# ═══════════════════════════════════════════════════════

class TestParsePlan:
    def test_parses_valid_json(self, agent, sample_candidates):
        text = '{"daily_plan": [{"day": 1, "attractions": [{"name": "故宫", "reason": "test", "duration_hours": 2.0}]}]}'
        result = agent._parse_plan(text, 2, sample_candidates)
        assert len(result) == 1

    def test_parses_code_block_json(self, agent, sample_candidates):
        text = '```json\n{"daily_plan": [{"day": 1, "attractions": []}]}\n```'
        result = agent._parse_plan(text, 1, sample_candidates)
        assert len(result) == 1

    def test_invalid_json_falls_back(self, agent, sample_candidates):
        result = agent._parse_plan("not json at all", 3, sample_candidates)
        assert len(result) == 3  # fallback creates per-day plans


# ═══════════════════════════════════════════════════════
# _fallback_plan（纯同步 + weather_impact）
# ═══════════════════════════════════════════════════════

class TestFallbackPlan:
    def test_creates_per_day_plans(self, agent, sample_candidates):
        result = agent._fallback_plan(sample_candidates, 2)
        assert len(result) == 2
        assert len(result[0]["attractions"]) >= 1

    def test_with_weather_penalty(self, agent, sample_candidates):
        weather = [{"day_of_trip": 1, "outdoor_suitability": 0.2}]
        result = agent._fallback_plan(sample_candidates, 1, weather)
        assert len(result) == 1

    def test_empty_candidates(self, agent):
        result = agent._fallback_plan([], 3)
        assert len(result) == 3
        assert all(len(d["attractions"]) == 0 for d in result)


# ═══════════════════════════════════════════════════════
# run() with mocks
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_run_with_rag_data(agent, sample_candidates, monkeypatch):
    """完整管线: RAG 返回候选 → LLM 规划"""
    async def fake_rag_search(*args, **kwargs):
        return sample_candidates

    async def fake_call_llm(self, messages, temperature=0.7, max_retries=3):
        return '{"daily_plan": [{"day": 1, "attractions": [{"name": "故宫", "reason": "经典", "duration_hours": 3.0, "price": 60, "latitude": 39.916, "longitude": 116.397, "tags": "历史;文化"}]}]}'

    monkeypatch.setattr("app.services.vector.rag.rag_search", fake_rag_search)
    monkeypatch.setattr(AttractionAgent, "call_llm", fake_call_llm)

    result = await agent.run({
        "destination": "北京", "days": 1,
        "preferences": ["历史"], "pace": "适中",
    })

    assert "daily_plan" in result
    assert result["candidate_count"] >= 1


@pytest.mark.asyncio
async def test_run_with_few_candidates_triggers_live_search(agent, sample_candidates, monkeypatch):
    """RAG 返回不足 3 个 → live_search 补充"""
    async def fake_rag(*args, **kwargs):
        return sample_candidates[:1]  # 只有1个

    async def fake_live_search(dest, limit=15):
        return sample_candidates[1:4]

    async def fake_call_llm(self, messages, temperature=0.7, max_retries=3):
        return '{"daily_plan": [{"day": 1, "attractions": []}]}'

    monkeypatch.setattr("app.services.vector.rag.rag_search", fake_rag)
    monkeypatch.setattr("app.services.third_party.poi_live.live_search_attractions", fake_live_search)
    monkeypatch.setattr(AttractionAgent, "call_llm", fake_call_llm)

    result = await agent.run({"destination": "北京", "days": 1})
    assert "daily_plan" in result


@pytest.mark.asyncio
async def test_run_exception_path(agent, monkeypatch):
    """RAG 失败时回退"""
    async def failing_rag(*args, **kwargs):
        raise RuntimeError("RAG down")

    async def fake_call_llm(self, messages, temperature=0.7, max_retries=3):
        return '{"daily_plan": []}'

    monkeypatch.setattr("app.services.vector.rag.rag_search", failing_rag)
    monkeypatch.setattr(AttractionAgent, "call_llm", fake_call_llm)

    result = await agent.run({"destination": "测试", "days": 1})
    assert "daily_plan" in result


@pytest.mark.asyncio
async def test_run_concurrent(agent, sample_candidates, monkeypatch):
    """并发安全: 3 个 run 同时执行"""
    async def fake_rag(*args, **kwargs):
        return sample_candidates

    async def fake_call_llm(self, messages, temperature=0.7, max_retries=3):
        return '{"daily_plan": [{"day": 1, "attractions": [{"name": "故宫", "reason": "test", "duration_hours": 2.0, "price": 0, "latitude": 39.9, "longitude": 116.4, "tags": ""}]}]}'

    monkeypatch.setattr("app.services.vector.rag.rag_search", fake_rag)
    monkeypatch.setattr(AttractionAgent, "call_llm", fake_call_llm)

    import asyncio
    tasks = [
        agent.run({"destination": "北京", "days": 1}),
        agent.run({"destination": "上海", "days": 2}),
        agent.run({"destination": "广州", "days": 1}),
    ]
    results = await asyncio.gather(*tasks)
    assert len(results) == 3
    for r in results:
        assert "daily_plan" in r
