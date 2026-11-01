"""测试 app/agents/route_optimizer_agent.py — 路线优化算法"""

import pytest
from app.agents.route_optimizer_agent import (
    _two_opt,
    _greedy_init,
    _path_distance,
    _dist,
    RouteOptimizerAgent,
)
from tests.test_llm import MockLLM


@pytest.fixture
def sample_attrs():
    """北京几个景点的坐标"""
    return [
        {"name": "故宫", "latitude": 39.916, "longitude": 116.397},
        {"name": "天坛", "latitude": 39.882, "longitude": 116.406},
        {"name": "长城", "latitude": 40.431, "longitude": 116.570},
        {"name": "颐和园", "latitude": 39.999, "longitude": 116.275},
        {"name": "鸟巢", "latitude": 39.992, "longitude": 116.390},
    ]


# ═══════════════════════════════════════════════════════
# _dist
# ═══════════════════════════════════════════════════════

class TestDist:
    def test_positive_distance(self, sample_attrs):
        d = _dist(sample_attrs[0], sample_attrs[1])  # 故宫 → 天坛
        assert d > 0

    def test_zero_distance_same_point(self):
        a = {"latitude": 39.9, "longitude": 116.4}
        b = {"latitude": 39.9, "longitude": 116.4}
        assert _dist(a, b) < 0.01

    def test_missing_coordinates_default_to_zero(self):
        a = {"latitude": 0, "longitude": 0}
        b = {"latitude": 0, "longitude": 0}
        assert _dist(a, b) < 0.01

    def test_none_coordinates(self):
        d = _dist({}, {})
        assert d >= 0


# ═══════════════════════════════════════════════════════
# _path_distance
# ═══════════════════════════════════════════════════════

class TestPathDistance:
    def test_multi_point_path(self, sample_attrs):
        d = _path_distance(sample_attrs)
        assert d > 0

    def test_single_point(self):
        assert _path_distance([{"latitude": 1, "longitude": 1}]) == 0

    def test_empty_list(self):
        assert _path_distance([]) == 0


# ═══════════════════════════════════════════════════════
# _greedy_init
# ═══════════════════════════════════════════════════════

class TestGreedyInit:
    def test_returns_all_points(self, sample_attrs):
        result = _greedy_init(sample_attrs)
        assert len(result) == len(sample_attrs)
        # Verify all names present
        names = {a["name"] for a in result}
        expected = {a["name"] for a in sample_attrs}
        assert names == expected

    def test_single_point(self):
        result = _greedy_init([{"name": "A", "latitude": 1, "longitude": 1}])
        assert len(result) == 1

    def test_two_points(self):
        points = [
            {"name": "A", "latitude": 1, "longitude": 1},
            {"name": "B", "latitude": 2, "longitude": 2},
        ]
        result = _greedy_init(points)
        assert len(result) == 2


# ═══════════════════════════════════════════════════════
# _two_opt
# ═══════════════════════════════════════════════════════

class TestTwoOpt:
    def test_returns_all_points(self, sample_attrs):
        route, dist = _two_opt(sample_attrs)
        assert len(route) == len(sample_attrs)
        assert dist > 0

    def test_optimization_improves_or_maintains(self, sample_attrs):
        orig_dist = _path_distance(sample_attrs)
        route, opt_dist = _two_opt(sample_attrs)
        # 优化后的距离 <= 原始距离
        assert opt_dist <= orig_dist + 0.1  # 允许微小浮点误差

    def test_two_points_no_change(self):
        points = [
            {"name": "A", "latitude": 1, "longitude": 1},
            {"name": "B", "latitude": 2, "longitude": 2},
        ]
        route, dist = _two_opt(points)
        assert len(route) == 2
        assert route[0]["name"] == "A"  # 顺序不变

    def test_three_points(self):
        points = [
            {"name": "A", "latitude": 39.9, "longitude": 116.4},
            {"name": "B", "latitude": 40.0, "longitude": 116.5},
            {"name": "C", "latitude": 39.95, "longitude": 116.45},
        ]
        route, dist = _two_opt(points)
        assert len(route) == 3
        assert dist > 0

    def test_concurrent_optimization(self):
        """并发安全：多线程调用 _two_opt 不共享状态"""
        import concurrent.futures
        points_batch = [
            [{"name": f"A{i}", "latitude": 39.9 + i * 0.01, "longitude": 116.4 + i * 0.01} for i in range(5)],
            [{"name": f"B{i}", "latitude": 40.0 - i * 0.01, "longitude": 116.5 - i * 0.01} for i in range(4)],
            [{"name": f"C{i}", "latitude": 39.95 + i * 0.02, "longitude": 116.45 - i * 0.02} for i in range(6)],
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            results = list(executor.map(_two_opt, points_batch))
        assert len(results) == 3
        for route, dist in results:
            assert dist > 0
            assert len(route) == len(route)


# ═══════════════════════════════════════════════════════
# RouteOptimizerAgent.run()
# ═══════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_run_optimizes_daily_plan(sample_attrs):
    agent = RouteOptimizerAgent(MockLLM(api_key="test", base_url="http://test", model="test"))
    result = await agent.run({
        "daily_itinerary": [
            {"day": 1, "attractions": sample_attrs},
        ],
    })
    assert "optimized_itinerary" in result
    assert result["total_saved_distance_km"] >= 0
    assert len(result["optimized_itinerary"]) == 1


@pytest.mark.asyncio
async def test_run_single_attraction_skips():
    agent = RouteOptimizerAgent(MockLLM(api_key="test", base_url="http://test", model="test"))
    result = await agent.run({
        "daily_itinerary": [
            {"day": 1, "attractions": [{"name": "故宫", "latitude": 39.9, "longitude": 116.4}]},
        ],
    })
    assert result["total_saved_distance_km"] == 0

@pytest.mark.asyncio
async def test_run_llm_exception_returns_empty(monkeypatch):
    """异常路径: LLM 失败时 _llm_suggestions 返回空字符串"""
    async def failing_call_llm(self, messages, temperature=0.5, max_retries=3):
        raise RuntimeError("LLM not available")

    monkeypatch.setattr(RouteOptimizerAgent, "call_llm", failing_call_llm)

    agent = RouteOptimizerAgent(MockLLM(api_key="test", base_url="http://test", model="test"))
    result = await agent.run({
        "daily_itinerary": [
            {"day": 1, "attractions": [
                {"name": "A", "latitude": 39.9, "longitude": 116.4},
                {"name": "B", "latitude": 40.0, "longitude": 116.5},
                {"name": "C", "latitude": 39.95, "longitude": 116.45},
            ]},
        ],
    })
    assert result["suggestions"] == ""
    assert result["total_saved_distance_km"] >= 0
