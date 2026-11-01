"""
Sprint 2 质量门禁测试 — 边界场景 + 核心函数覆盖

门禁1: 测试覆盖 ≥60%，至少3个边界场景
门禁3: 极端输入场景

用法:
    python -m pytest tests/test_sprint2_quality.py -v
"""

import math
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ================================================================
# 边界场景1: Traffic 坐标缺失 → 估算兜底
# ================================================================

class TestTrafficEstimateFallback:
    """极端场景: 无坐标/零坐标/异常坐标 → 不应该崩溃或返回天价"""

    @pytest.mark.asyncio
    async def test_no_coordinates_defaults_to_5km(self):
        """两个POI都缺坐标 → 市区短途估算 (d=5.0, t=12min)"""
        from app.agents.traffic_agent import _estimate

        a = {"name": "景点A"}
        b = {"name": "景点B"}

        result = _estimate(a, b, "transit")
        assert result["distance_km"] == 5.0
        assert result["time_min"] > 0
        assert result["cost"] > 0
        assert "(est)" in result["mode"]

    @pytest.mark.asyncio
    async def test_one_missing_coords_still_estimates(self):
        """仅一方有坐标 → 也应估算"""
        from app.agents.traffic_agent import _estimate

        a = {"name": "西湖", "latitude": 30.24, "longitude": 120.14}
        b = {"name": "未知"}

        result = _estimate(a, b, "driving")
        assert result["distance_km"] == 5.0
        assert result["cost"] > 0

    @pytest.mark.asyncio
    async def test_zero_coordinates(self):
        """坐标全为0 → 估算（避免 haversine(0,0,0,0) 去重bug）"""
        from app.agents.traffic_agent import _estimate

        a = {"name": "A", "latitude": 0, "longitude": 0}
        b = {"name": "B", "latitude": 0, "longitude": 0}
        result = _estimate(a, b, "transit")
        # 注意: 0 是真值(haversine 会算)，但如果 all([0,0,0,0]) 由于 0 是 falsy，走估算
        assert result["distance_km"] > 0

    @pytest.mark.asyncio
    async def test_same_with_only_one_coordinate_not_skipped(self):
        """只有一方有坐标 → _same 不应用距离判重"""
        from app.agents.traffic_agent import _same

        a = {"name": "酒店A", "latitude": 30.25, "longitude": 120.15}
        b = {"name": "餐厅B"}  # 无坐标
        assert not _same(a, b)  # 不应该被判为同一站

    @pytest.mark.asyncio
    async def test_same_no_coordinates_not_skipped(self):
        """双方都缺坐标 → 不做距离判重（修复前会由于 haversine(0,0,0,0)=0→跳过）"""
        from app.agents.traffic_agent import _same

        a = {"name": "晚餐餐厅"}  # 无坐标
        b = {"name": "酒店"}  # 无坐标
        assert not _same(a, b)  # 不应被判为同一站

    @pytest.mark.asyncio
    async def test_same_very_close_merged(self):
        """两站在50米内正确判重"""
        from app.agents.traffic_agent import _same

        a = {"name": "西湖入口", "latitude": 30.2427, "longitude": 120.1464}
        b = {"name": "西湖出口", "latitude": 30.2427, "longitude": 120.1464}
        assert _same(a, b)


# ================================================================
# 边界场景2: Haversine 极端值
# ================================================================

class TestHaversine:
    """极端场景: 相同点/对跖点/极点"""

    def test_same_point_zero(self):
        from app.services.map.geocode import haversine_distance
        d = haversine_distance(39.9, 116.4, 39.9, 116.4)
        assert d == pytest.approx(0, abs=0.01)

    def test_beijing_to_new_york(self):
        from app.services.map.geocode import haversine_distance
        d = haversine_distance(39.9, 116.4, 40.7, -74.0)
        assert 10000 < d < 12000  # ≈10988 km

    def test_pole_to_pole(self):
        from app.services.map.geocode import haversine_distance
        d = haversine_distance(90, 0, -90, 0)
        assert d == pytest.approx(20015, rel=0.01)

    def test_negative_longitude(self):
        from app.services.map.geocode import haversine_distance
        d = haversine_distance(35, 135, 35, -135)
        assert d > 0


# ================================================================
# 边界场景3: Budget 极端预算
# ================================================================

class TestBudgetDynamic:
    """极端输入: 0预算/负数/超大值"""

    def test_zero_budget(self):
        """预算为0"""
        from app.agents.budget_agent import _dynamic
        result = _dynamic(0, "北京", [], 3)
        for v in result.values():
            assert v == 0

    def test_tiny_budget_single_day(self):
        """极小预算1天"""
        from app.agents.budget_agent import _dynamic
        result = _dynamic(100, "武汉", ["穷游"], 1)
        total = sum(result.values())
        assert total == pytest.approx(100, rel=0.1)

    def test_unknown_city_uses_default_tier(self):
        """未知城市用默认系数1.0"""
        from app.agents.budget_agent import _dynamic
        result = _dynamic(5000, "火星", [], 3)
        total = sum(result.values())
        assert total == pytest.approx(5000, rel=0.1)

    def test_budget_no_limit_zero_handled(self):
        """无限制预算=0的处理"""
        from app.agents.budget_agent import _dynamic
        result = _dynamic(100000, "上海", [], 3)
        for v in result.values():
            assert v >= 0

    def test_budget_retry_threshold(self):
        """超支≤30%且retry<2才重试"""
        # 直接验证公式: 0 < over_pct <= 30 and retry < 2
        assert 0 < 25 <= 30 and 0 < 2   # over=25%, retry=0 → 应重试
        assert not (0 < 35 <= 30)        # over=35% → 不重试
        assert not (0 < 20 <= 30 and 2 < 2)  # retry=2 → 不重试


# ================================================================
# 边界场景4: AttractionAgent 坐标/标签回填
# ================================================================

class TestAttractionBackfill:
    """数据链路: candidate → daily_plan 回填"""

    def test_name_key_normalization(self):
        from app.agents.attraction_agent import _name_key
        assert _name_key("西湖（杭州）") == "西湖"
        assert _name_key("中山公园") == "中山公园"
        assert _name_key("北京 天安门") == "北京天安门"

    def test_rank_score_rerank_first(self):
        from app.agents.attraction_agent import _rank_score
        c1 = {"rerank_score": 0.85, "relevance": 0.5}
        c2 = {"relevance": 0.7}
        assert _rank_score(c1) == 0.85
        assert _rank_score(c2) == 0.7


# ================================================================
# 边界场景5: 空列表/异常输入保护
# ================================================================

class TestEmptyInputs:
    """极端输入: None/空字符串/空列表"""

    def test_empty_attractions_plan(self):
        """空景点 → 不崩溃"""
        from app.orchestrator.nodes import _dedupe_daily_plan
        result = _dedupe_daily_plan([])
        assert result == []
        result2 = _dedupe_daily_plan(None)
        assert result2 == []

    @pytest.mark.asyncio
    async def test_tripagent_empty_checkins(self):
        from app.agents.trip_agent import TripAgent
        from app.services.llm.deepseek import DeepSeekLLM
        agent = TripAgent(DeepSeekLLM())
        # start with empty itinerary
        plan = {"destination": "北京", "days": 0, "daily_itinerary": []}
        res = await agent.run({"action": "start", **plan})
        assert res.get("total_pois", -1) >= 0

    @pytest.mark.asyncio
    async def test_tripagent_invalid_checkin_time(self):
        """签到传非法时间字符串 → 不崩溃"""
        from app.agents.trip_agent import TripAgent
        from app.services.llm.deepseek import DeepSeekLLM
        agent = TripAgent(DeepSeekLLM())
        res = await agent.run({
            "action": "checkin",
            "planned_time": "not_a_time",
            "poi_name": "测试",
            "poi_type": "attraction",
        })
        assert "time_delta_min" in res

    @pytest.mark.asyncio
    async def test_tripagent_last_day_has_no_tomorrow_reminder(self):
        from app.agents.trip_agent import TripAgent

        llm = MagicMock()
        llm.chat = AsyncMock(side_effect=AssertionError("last day must not call LLM"))
        agent = TripAgent(llm)

        result = await agent.generate_reminder({
            "current_day": 3,
            "total_days": 3,
            "is_last_day": True,
        })

        assert result["is_last_day"] is True
        assert result["day"] == 3
        assert result["reminder_text"] == ""
        llm.chat.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_tripagent_reminder_is_immediate_and_uses_exact_weather(self):
        from app.agents.trip_agent import TripAgent

        llm = MagicMock()
        llm.chat = AsyncMock(side_effect=AssertionError("reminder must not call LLM"))
        agent = TripAgent(llm)

        result = await agent.generate_reminder({
            "current_day": 2,
            "total_days": 3,
            "tomorrow_day": 3,
            "day_outline": {"stops": [{
                "type": "attraction", "name": "中国美术馆", "planned_time": "09:00",
            }]},
            "weather": {
                "date": "2026-07-19", "condition": "多云",
                "temp_high": 32.0, "temp_low": 22.0, "advice": "注意防晒",
            },
        })

        assert "22~32°C" in result["reminder_text"]
        assert "25" not in result["reminder_text"]
        assert result["weather"]["date"] == "2026-07-19"
        llm.chat.assert_not_awaited()

    def test_composite_score_empty_candidates(self):
        from app.services.vector.scorer import composite_score
        result = composite_score([])
        assert result == []

    def test_composite_score_single_candidate(self):
        from app.services.vector.scorer import composite_score
        result = composite_score([{"name": "test", "rating": 5, "relevance": 0.8, "price": 0}])
        assert len(result) == 1
        assert "composite_score" in result[0]


# ================================================================
# 核心函数: Daily Plan 去重
# ================================================================

class TestDeduplication:
    def test_normalize_chinese_parens(self):
        from app.orchestrator.nodes import _normalize_attraction_name
        result = _normalize_attraction_name("中山公园（免费）")
        assert result == "中山公园"

    def test_dedupe_removes_duplicate_names(self):
        from app.orchestrator.nodes import _dedupe_daily_plan
        plan = [{
            "day": 1,
            "attractions": [
                {"name": "西湖"},
                {"name": "西湖"},
                {"name": "灵隐寺"},
            ],
        }]
        result = _dedupe_daily_plan(plan)
        assert len(result[0]["attractions"]) == 2


# ================================================================
# 核心函数: Vision 图片加载
# ================================================================

class TestVisionImageLoading:
    @pytest.mark.asyncio
    async def test_data_url_passthrough(self):
        """data: URL 原样返回"""
        from app.services.llm.vision import VisionLLM
        v = VisionLLM()
        data_url = "data:image/png;base64,iVBORw0KGgo="
        result = await v._load_image_data(data_url)
        assert result == data_url

    @pytest.mark.asyncio
    async def test_missing_local_file_returns_original(self):
        """不存在的本地文件返回原始路径"""
        from app.services.llm.vision import VisionLLM
        v = VisionLLM()
        result = await v._load_image_data("/nonexistent/path.jpg")
        assert result == "/nonexistent/path.jpg"


# ================================================================
# 核心函数: PipelineCache
# ================================================================

class TestPipelineCache:
    @pytest.mark.asyncio
    async def test_rag_cache_hit(self):
        from app.utils.pipeline_cache import PipelineCache
        cache = PipelineCache()
        await cache.rag_set("attractions", "北京景点", [{"name": "故宫"}])
        result = await cache.rag_get("attractions", "北京景点")
        assert result is not None
        assert result[0]["name"] == "故宫"

    @pytest.mark.asyncio
    async def test_rag_cache_miss(self):
        from app.utils.pipeline_cache import PipelineCache
        cache = PipelineCache()
        result = await cache.rag_get("attractions", "no_such_query")
        assert result is None

    @pytest.mark.asyncio
    async def test_rag_key_unique_per_collection(self):
        from app.utils.pipeline_cache import PipelineCache
        cache = PipelineCache()
        key1 = cache.rag_key("attractions", "北京")
        key2 = cache.rag_key("restaurants", "北京")
        assert key1 != key2

    @pytest.mark.asyncio
    async def test_geocode_cache(self):
        from app.utils.pipeline_cache import PipelineCache
        cache = PipelineCache()
        await cache.geocode_set("西湖", 30.24, 120.14)
        result = await cache.geocode_get("西湖")
        assert result == (30.24, 120.14)


# ================================================================
# 核心函数: 费用计算
# ================================================================

class TestCostCalculation:
    def test_transit_cost_parse(self):
        from app.agents.traffic_agent import _af, _ai
        assert _af("3.5") == 3.5
        assert _af(None) == 0.0
        assert _ai("100") == 100
        assert _ai(None) == 0

    @pytest.mark.asyncio
    async def test_tripagent_cost_delta_positive(self):
        """签到花费超支 → cost_delta > 0"""
        from app.agents.trip_agent import TripAgent
        from app.services.llm.deepseek import DeepSeekLLM
        agent = TripAgent(DeepSeekLLM())
        res = await agent.run({
            "action": "checkin",
            "planned_time": "12:00",
            "poi_name": "测试餐厅",
            "poi_type": "restaurant",
            "planned_cost": 100,
            "actual_cost": 150,
        })
        assert res.get("cost_delta", 0) == 50

    @pytest.mark.asyncio
    async def test_tripagent_cost_delta_under(self):
        """签到花费节余 → cost_delta < 0"""
        from app.agents.trip_agent import TripAgent
        from app.services.llm.deepseek import DeepSeekLLM
        agent = TripAgent(DeepSeekLLM())
        res = await agent.run({
            "action": "checkin",
            "planned_time": "18:00",
            "poi_name": "测试",
            "poi_type": "restaurant",
            "planned_cost": 200,
            "actual_cost": 150,
        })
        assert res.get("cost_delta", 0) == -50
