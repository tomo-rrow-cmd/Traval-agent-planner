"""测试 app/agents/budget_agent.py — 纯函数 + run() 边界"""

import pytest
from app.agents.budget_agent import _dynamic, _suggest, _adj, BudgetAgent, CITY_TIER, BASE
from tests.test_llm import MockLLM


class TestDynamic:
    def test_basic_allocation(self):
        result = _dynamic(5000, "北京", [], 5)
        assert sum(result.values()) == pytest.approx(5000, rel=0.01)
        assert "住宿" in result
        assert "交通" in result
        assert "餐饮" in result
        assert "门票" in result
        assert "购物" in result

    def test_tier_adjusts_hotel_for_expensive_city(self):
        """北京 tier=1.4 → 住宿比例上调"""
        result = _dynamic(10000, "北京", [], 3)
        base = _dynamic(10000, "武汉", [], 3)  # 武汉 tier=0.9
        # 北京住宿比例 > 武汉
        assert result["住宿"] > base["住宿"]

    def test_food_preference_increases_dining(self):
        without_food = _dynamic(5000, "北京", [], 3)
        with_food = _dynamic(5000, "北京", ["美食", "火锅"], 3)
        assert with_food["餐饮"] > without_food["餐饮"]

    def test_budget_preference_shifts(self):
        """穷游偏好 → 住宿降、门票升"""
        result = _dynamic(5000, "武汉", ["穷游", "省钱"], 3)
        base = _dynamic(5000, "武汉", [], 3)
        assert result["住宿"] < base["住宿"]
        assert result["门票"] > base["门票"]

    def test_short_trip_adjusts_transport(self):
        """≤2天 → 交通↑、住宿↓"""
        short = _dynamic(5000, "武汉", [], 2)
        long = _dynamic(5000, "武汉", [], 5)
        assert short["交通"] > long["交通"]

    def test_unknown_city_uses_default_tier(self):
        result = _dynamic(5000, "火星基地", [], 3)
        assert sum(result.values()) == pytest.approx(5000, rel=0.01)

    def test_empty_prefs(self):
        result = _dynamic(3000, "成都", None, 4)
        assert sum(result.values()) == pytest.approx(3000, rel=0.01)

    def test_ratio_clamped(self):
        """超贵城市 tier被 clamp 到 1.6"""
        # 三亚 tier=1.5 → clamp to 1.5
        normal = _dynamic(10000, "武汉", [], 3)
        expensive = _dynamic(10000, "三亚", [], 3)
        assert expensive["住宿"] > normal["住宿"]


class TestSuggest:
    def test_over_budget_suggestions(self):
        details = [
            {"category": "住宿", "budget": 1000, "spent": 1500, "remaining": -500, "status": "over"},
            {"category": "餐饮", "budget": 500, "spent": 800, "remaining": -300, "status": "over"},
        ]
        result = _suggest(details, 25, 0)
        assert len(result) >= 3  # 2 for 住宿 + 1 for 餐饮

    def test_high_overage_with_retry0_suggests_increase(self):
        details = [{"category": "住宿", "budget": 1000, "spent": 2000, "remaining": -1000, "status": "over"}]
        result = _suggest(details, 35, 0)
        assert result[0]["action"] == "建议提高总预算"

    def test_transport_overage(self):
        details = [{"category": "交通", "budget": 500, "spent": 800, "remaining": -300, "status": "over"}]
        result = _suggest(details, 10, 0)
        assert result[0]["action"] == "地铁替代打车"

    def test_ticket_overage(self):
        details = [{"category": "门票", "budget": 200, "spent": 500, "remaining": -300, "status": "over"}]
        result = _suggest(details, 10, 0)
        assert result[0]["action"] == "换免费景点"

    def test_ok_status_no_suggestions(self):
        details = [{"category": "住宿", "budget": 1000, "spent": 900, "remaining": 100, "status": "ok"}]
        result = _suggest(details, 5, 0)
        assert result == []


class TestAdj:
    def test_hotel_overage_first_retry(self):
        details = [{"category": "住宿", "budget": 1000, "spent": 1500, "remaining": -500, "status": "over"}]
        result = _adj(details, 0)
        assert "hotel_budget" in result
        assert result["hotel_budget"] >= 200
        assert result["hotel_star"] == 2

    def test_hotel_overage_not_first_retry(self):
        """retry > 0 时不调整住宿"""
        details = [{"category": "住宿", "budget": 1000, "spent": 1500, "remaining": -500, "status": "over"}]
        result = _adj(details, 1)
        assert "hotel_budget" not in result

    def test_meal_overage(self):
        details = [{"category": "餐饮", "budget": 500, "spent": 800, "remaining": -300, "status": "over"}]
        result = _adj(details, 0)
        assert "meal_budget" in result
        assert result["meal_budget"] >= 50

    def test_ok_status_no_adjustment(self):
        details = [{"category": "住宿", "budget": 1000, "spent": 900, "remaining": 100, "status": "ok"}]
        result = _adj(details, 0)
        assert result == {}

    def test_floor_values_respected(self):
        """spent=100 → 70，但 floor=200 → 最终 hotel_budget=200"""
        details = [{"category": "住宿", "budget": 500, "spent": 100, "remaining": 400, "status": "over"}]
        result = _adj(details, 0)
        assert result["hotel_budget"] == 200


# ── BudgetAgent.run() 边界分支 ──────────────────────────

class TestBudgetAgentRun:
    @pytest.mark.asyncio
    async def test_preferences_not_a_list(self):
        """preferences 不是 list → [str(prefs)]"""
        agent = BudgetAgent(MockLLM(api_key="test", base_url="http://test", model="test"))
        result = await agent.run({
            "total_budget": 5000,
            "days": 3,
            "travelers": 2,
            "destination": "北京",
            "origin": "上海",
            "preferences": "美食",
            "daily_itinerary": [],
            "meal_plan": [],
            "hotel_plan": {},
            "traffic": {"total_traffic_cost": 0},
        })
        assert "warnings" in result

    @pytest.mark.asyncio
    async def test_expense_over_budget_triggers_warnings(self):
        """实际花费超过预算 → 超预算警告"""
        agent = BudgetAgent(MockLLM(api_key="test", base_url="http://test", model="test"))
        result = await agent.run({
            "total_budget": 5000,
            "planning_budget": 5000,
            "days": 3,
            "travelers": 1,
            "destination": "北京",
            "origin": "上海",
            "preferences": [],
            "expenses": {
                "hotels": 3500,  # 远超预算比例
                "traffic": 1500,
                "meals": 1000,
                "attractions": 500,
                "shopping": 0,
            },
            "daily_itinerary": [],
            "meal_plan": [],
            "hotel_plan": {},
            "traffic": {"total_traffic_cost": 1500},
        })
        assert "warnings" in result
        assert any("超预算" in w or "超规划预算" in w for w in result.get("warnings", []))

    @pytest.mark.asyncio
    async def test_expense_near_limit_triggers_close_warning(self):
        """实际花费接近预算上限 (85%-100%) → 接近上限警告"""
        agent = BudgetAgent(MockLLM(api_key="test", base_url="http://test", model="test"))
        result = await agent.run({
            "total_budget": 5000,
            "planning_budget": 5000,
            "days": 3,
            "travelers": 1,
            "destination": "北京",
            "origin": "上海",
            "preferences": [],
            "expenses": {
                "hotels": 1750,
                "traffic": 1000,
                "meals": 1000,
                "attractions": 750,
                "shopping": 0,
            },  # sum = 4500 → 90% of planning, triggers "接近上限"
            "daily_itinerary": [],
            "meal_plan": [],
            "hotel_plan": {},
            "traffic": {"total_traffic_cost": 1000},
        })
        warnings = result.get("warnings", [])
        assert any("接近上限" in w for w in warnings)
