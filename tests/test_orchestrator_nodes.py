"""测试 app/orchestrator/nodes.py — 编排器节点"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ── helpers ──────────────────────────────────────────────────

@pytest.fixture
def base_state():
    return {
        "destination": "北京",
        "origin": "上海",
        "start_date": "2099-08-01",
        "end_date": "2099-08-03",
        "days": 3,
        "total_budget": 6000,
        "reserve_budget": 0,
        "planning_budget": 6000,
        "travelers": 2,
        "preferences": ["美食", "文化"],
        "cuisine_preferences": ["川菜"],
        "pace": "适中",
        "preferred_transport": "地铁",
        "hotel_star": 4,
        "hotel_budget": 500,
        "meal_budget": 100,
        "weather_forecast": [],
        "weather_impact": [],
        "weather_status": "fallback",
        "daily_plan": [],
        "meal_plan": [],
        "hotel_plan": {},
        "traffic": {"total_traffic_cost": 0},
        "big_traffic": {},
        "meituan_hotels": [],
        "attraction_details": [],
        "food_details": [],
        "retry_count": 0,
        "adjusted_params": {},
    }


def mock_agent_run(monkeypatch, agent_path, return_value):
    """Mock an Agent class so .run() returns a preset dict."""
    mock_cls = MagicMock()
    mock_cls.return_value.run = AsyncMock(return_value=return_value)
    monkeypatch.setattr(agent_path, mock_cls)


# ═══════════════════════════════════════════════════════
# node_weather
# ═══════════════════════════════════════════════════════

class TestNodeWeather:
    @pytest.mark.asyncio
    async def test_success_path(self, monkeypatch, base_state):
        mock_agent = MagicMock()
        mock_agent.return_value.generate_impact_factors = AsyncMock(return_value={
            "forecasts": [{"dayweather": "晴", "daytemp": "25", "nightweather": "多云", "nighttemp": "15"}],
            "impacts": [{"walking_viable": True} for _ in range(3)],
        })
        monkeypatch.setattr("app.agents.weather_agent.WeatherAgent", mock_agent)

        from app.orchestrator.nodes import node_weather
        result = await node_weather(base_state)

        assert result["weather_status"] == "success"
        assert len(result["weather_forecast"]) == 1
        assert "summary" in result["weather_forecast"][0]
        kwargs = mock_agent.return_value.generate_impact_factors.await_args.kwargs
        assert kwargs["start_date"] == "2099-08-01"
        assert kwargs["end_date"] == "2099-08-03"

    @pytest.mark.asyncio
    async def test_fallback_on_exception(self, monkeypatch, base_state):
        mock_agent = MagicMock()
        mock_agent.return_value.generate_impact_factors = AsyncMock(
            side_effect=RuntimeError("API error")
        )
        monkeypatch.setattr("app.agents.weather_agent.WeatherAgent", mock_agent)

        from app.orchestrator.nodes import node_weather
        result = await node_weather(base_state)

        assert result["weather_status"] == "fallback"
        assert len(result["weather_impact"]) == 3  # build_neutral_impacts

    @pytest.mark.asyncio
    async def test_no_forecast_keeps_fallback_status(self, monkeypatch, base_state):
        mock_agent = MagicMock()
        mock_agent.return_value.generate_impact_factors = AsyncMock(return_value={
            "forecasts": [],
            "impacts": [{"day_of_trip": day} for day in range(1, 4)],
        })
        monkeypatch.setattr("app.agents.weather_agent.WeatherAgent", mock_agent)

        from app.orchestrator.nodes import node_weather
        result = await node_weather(base_state)

        assert result["weather_status"] == "fallback"
        assert len(result["weather_impact"]) == 3


# ═══════════════════════════════════════════════════════
# _dedupe_daily_plan
# ═══════════════════════════════════════════════════════

class TestDedupeDailyPlan:
    def test_removes_duplicate_attractions(self):
        from app.orchestrator.nodes import _dedupe_daily_plan
        plan = [
            {"day": 1, "attractions": [
                {"name": "故宫"}, {"name": "故宫"}, {"name": "天坛"},
            ]},
        ]
        result = _dedupe_daily_plan(plan)
        assert len(result[0]["attractions"]) == 2

    def test_empty_plan(self):
        from app.orchestrator.nodes import _dedupe_daily_plan
        assert _dedupe_daily_plan([]) == []
        assert _dedupe_daily_plan(None) == []


class TestNormalizeAttractionName:
    def test_normalizes_chinese_parens(self):
        from app.orchestrator.nodes import _normalize_attraction_name
        assert _normalize_attraction_name("故宫（紫禁城）") == "故宫"


# ═══════════════════════════════════════════════════════
# node_parallel_planning
# ═══════════════════════════════════════════════════════

class TestNodeParallelPlanning:
    @pytest.mark.asyncio
    async def test_gathers_three_agents(self, monkeypatch, base_state):
        mock_agent_cls = MagicMock()
        mock_agent_cls.return_value.run = AsyncMock(return_value={
            "daily_plan": [], "meal_plan": [], "hotel_plan": {},
        })
        monkeypatch.setattr("app.orchestrator.nodes.AttractionAgent", mock_agent_cls)
        monkeypatch.setattr("app.orchestrator.nodes.FoodAgent", mock_agent_cls)
        monkeypatch.setattr("app.orchestrator.nodes.HotelAgent", mock_agent_cls)

        from app.orchestrator.nodes import node_parallel_planning
        result = await node_parallel_planning(base_state)

        assert "daily_plan" in result
        assert "meal_plan" in result
        assert "hotel_plan" in result
        assert result["current_stage"] == "parallel_planning"

    @pytest.mark.asyncio
    async def test_passes_cuisine_preferences_to_food_agent(self, monkeypatch, base_state):
        captured = {}

        attr_cls = MagicMock()
        attr_cls.return_value.run = AsyncMock(return_value={"daily_plan": []})
        hotel_cls = MagicMock()
        hotel_cls.return_value.run = AsyncMock(return_value={"hotel_plan": {}})

        class FoodSpy:
            def __init__(self, llm):
                pass

            async def run(self, payload):
                captured.update(payload)
                return {"meal_plan": []}

        monkeypatch.setattr("app.orchestrator.nodes.AttractionAgent", attr_cls)
        monkeypatch.setattr("app.orchestrator.nodes.FoodAgent", FoodSpy)
        monkeypatch.setattr("app.orchestrator.nodes.HotelAgent", hotel_cls)
        base_state["cuisine_preferences"] = ["川菜", "烤鸭"]

        from app.orchestrator.nodes import node_parallel_planning
        await node_parallel_planning(base_state)

        assert captured["cuisine_preferences"] == ["川菜", "烤鸭"]

    @pytest.mark.asyncio
    async def test_empty_cuisine_does_not_fallback_to_travel_preferences(self, monkeypatch, base_state):
        captured = {}
        attr_cls = MagicMock()
        attr_cls.return_value.run = AsyncMock(return_value={"daily_plan": []})
        hotel_cls = MagicMock()
        hotel_cls.return_value.run = AsyncMock(return_value={"hotel_plan": {}})

        class FoodSpy:
            def __init__(self, llm):
                pass

            async def run(self, payload):
                captured.update(payload)
                return {"meal_plan": []}

        monkeypatch.setattr("app.orchestrator.nodes.AttractionAgent", attr_cls)
        monkeypatch.setattr("app.orchestrator.nodes.FoodAgent", FoodSpy)
        monkeypatch.setattr("app.orchestrator.nodes.HotelAgent", hotel_cls)
        base_state["cuisine_preferences"] = []

        from app.orchestrator.nodes import node_parallel_planning
        await node_parallel_planning(base_state)

        assert captured["cuisine_preferences"] == []


# ═══════════════════════════════════════════════════════
# decision r1 / r2 / detail_enrich / traffic
# ═══════════════════════════════════════════════════════

class TestDecisionNodes:
    @pytest.mark.asyncio
    async def test_node_decision_r1(self, monkeypatch, base_state):
        base_state["daily_plan"] = [{"day": 1, "attractions": [{"name": "故宫"}]}]
        base_state["meal_plan"] = [{"day": 1, "meals": []}]

        mock_cls = MagicMock()
        mock_cls.return_value.run_round1 = AsyncMock(return_value={
            "daily_plan": base_state["daily_plan"],
            "meal_plan": base_state["meal_plan"],
        })
        monkeypatch.setattr("app.orchestrator.nodes.DecisionAgent", mock_cls)

        from app.orchestrator.nodes import node_decision_r1
        result = await node_decision_r1(base_state)
        assert result["current_stage"] == "decision_r1"

    @pytest.mark.asyncio
    async def test_node_decision_r2(self, monkeypatch, base_state):
        mock_cls = MagicMock()
        mock_cls.return_value.run_round2 = AsyncMock(return_value={
            "hotel_plan": {"selected": "hotel1"},
        })
        monkeypatch.setattr("app.orchestrator.nodes.DecisionAgent", mock_cls)

        from app.orchestrator.nodes import node_decision_r2
        result = await node_decision_r2(base_state)
        assert result["current_stage"] == "decision_r2"

    @pytest.mark.asyncio
    async def test_node_detail_enrich(self, monkeypatch, base_state):
        mock_cls = MagicMock()
        mock_cls.return_value.run = AsyncMock(return_value={
            "attraction_details": [], "food_details": [],
        })
        monkeypatch.setattr("app.agents.detail_agent.DetailAgent", mock_cls)

        from app.orchestrator.nodes import node_detail_enrich
        result = await node_detail_enrich(base_state)
        assert result["current_stage"] == "detail_enrich"

    @pytest.mark.asyncio
    async def test_node_traffic(self, monkeypatch, base_state):
        mock_cls = MagicMock()
        mock_cls.return_value.run = AsyncMock(return_value={
            "big_traffic": {}, "time_warnings": [],
        })
        monkeypatch.setattr("app.orchestrator.nodes.TrafficAgent", mock_cls)

        from app.orchestrator.nodes import node_traffic
        result = await node_traffic(base_state)
        assert result["current_stage"] == "traffic"

    @pytest.mark.asyncio
    async def test_node_traffic_receives_selected_hotel(self, monkeypatch, base_state):
        captured = {}

        class TrafficSpy:
            def __init__(self, llm):
                pass

            async def run(self, payload):
                captured.update(payload)
                return {"big_traffic": {}, "time_warnings": []}

        monkeypatch.setattr("app.orchestrator.nodes.TrafficAgent", TrafficSpy)
        base_state["hotel_plan"] = {
            "selected": "如家酒店",
            "selected_hotel": {"name": "如家酒店", "latitude": 39.9, "longitude": 116.4},
            "recommendations": [
                {"name": "北京饭店", "latitude": 39.8, "longitude": 116.3},
                {"name": "如家酒店", "latitude": 39.9, "longitude": 116.4},
            ],
        }

        from app.orchestrator.nodes import node_traffic
        await node_traffic(base_state)

        assert captured["hotel_plan"]["selected_hotel"]["name"] == "如家酒店"
        assert captured["start_date"] == "2099-08-01"
        assert captured["end_date"] == "2099-08-03"


# ═══════════════════════════════════════════════════════
# node_budget
# ═══════════════════════════════════════════════════════

class TestNodeBudget:
    @pytest.mark.asyncio
    async def test_basic_budget_run(self, monkeypatch, base_state):
        mock_cls = MagicMock()
        mock_cls.return_value.run = AsyncMock(return_value={
            "final_plan": {
                "daily_itinerary": [],
                "budget": {"details": []},
            },
            "should_retry": False,
            "adjusted_params": {},
            "retry_count": 0,
        })
        monkeypatch.setattr("app.orchestrator.nodes.BudgetAgent", mock_cls)

        from app.orchestrator.nodes import node_budget
        result = await node_budget(base_state)
        assert result["current_stage"] == "completed"
        assert result["should_retry"] is False

    @pytest.mark.asyncio
    async def test_selected_hotel_fallback_to_recommendations(self, monkeypatch, base_state):
        mock_cls = MagicMock()
        mock_cls.return_value.run = AsyncMock(return_value={
            "final_plan": {
                "daily_itinerary": [],
                "budget": {"details": []},
            },
            "should_retry": False,
            "adjusted_params": {},
            "retry_count": 0,
        })
        monkeypatch.setattr("app.orchestrator.nodes.BudgetAgent", mock_cls)

        base_state["hotel_plan"] = {
            "selected_hotel": None,
            "selected": None,
            "recommendations": [{"name": "唯一酒店", "total": 1500}],
        }

        from app.orchestrator.nodes import node_budget
        result = await node_budget(base_state)
        assert result["should_retry"] is False

    @pytest.mark.asyncio
    async def test_selected_hotel_by_name(self, monkeypatch, base_state):
        mock_cls = MagicMock()
        mock_cls.return_value.run = AsyncMock(return_value={
            "final_plan": {
                "daily_itinerary": [],
                "budget": {"details": [{"category": "住宿", "spent": 0, "budget": 1000, "status": "ok"}]},
            },
            "should_retry": False,
            "adjusted_params": {},
            "retry_count": 0,
        })
        monkeypatch.setattr("app.orchestrator.nodes.BudgetAgent", mock_cls)

        base_state["hotel_plan"] = {
            "selected": "如家酒店",
            "selected_hotel": None,
            "recommendations": [
                {"name": "北京饭店", "total": 3000},
                {"name": "如家酒店", "total": 800},
            ],
        }

        from app.orchestrator.nodes import node_budget
        result = await node_budget(base_state)
        assert result["current_stage"] == "completed"

    @pytest.mark.asyncio
    async def test_weather_injection_into_itinerary(self, monkeypatch, base_state):
        mock_cls = MagicMock()
        mock_cls.return_value.run = AsyncMock(return_value={
            "final_plan": {
                "daily_itinerary": [{"day": 1}, {"day": 2}, {"day": 3}],
                "budget": {"details": []},
            },
            "should_retry": False,
            "adjusted_params": {},
            "retry_count": 0,
        })
        monkeypatch.setattr("app.orchestrator.nodes.BudgetAgent", mock_cls)

        base_state["weather_forecast"] = [
            {"date": "2099-08-01", "summary": "晴 25°C / 15°C"},
            {"date": "2099-08-03", "summary": "雨 18°C / 8°C"},
        ]
        base_state["weather_impact"] = [
            {
                "date": "2099-08-02",
                "dayweather": "未知",
                "daytemp": 22,
                "nighttemp": 15,
            },
        ]
        base_state["weather_status"] = "success"

        from app.orchestrator.nodes import node_budget
        result = await node_budget(base_state)
        itinerary = result["final_plan"]["daily_itinerary"]
        assert [day["date"] for day in itinerary] == [
            "2099-08-01",
            "2099-08-02",
            "2099-08-03",
        ]
        assert [day["date_label"] for day in itinerary] == [
            "8月1日",
            "8月2日",
            "8月3日",
        ]
        assert itinerary[0]["weather_summary"] == "晴 25°C / 15°C"
        assert itinerary[1]["weather_summary"] == "未知 22°C / 15°C"
        assert itinerary[2]["weather_summary"] == "雨 18°C / 8°C"

    @pytest.mark.asyncio
    async def test_no_data_marking(self, monkeypatch, base_state):
        mock_cls = MagicMock()
        mock_cls.return_value.run = AsyncMock(return_value={
            "final_plan": {
                "daily_itinerary": [],
                "budget": {"details": [
                    {"category": "购物", "spent": 0, "budget": 500, "status": "ok"},
                ]},
            },
            "should_retry": False,
            "adjusted_params": {},
            "retry_count": 0,
        })
        monkeypatch.setattr("app.orchestrator.nodes.BudgetAgent", mock_cls)

        from app.orchestrator.nodes import node_budget
        result = await node_budget(base_state)
        final = result["final_plan"]
        assert final["budget"]["details"][0]["status"] == "no_data"

    @pytest.mark.asyncio
    async def test_passes_budget_semantics_to_budget_agent(self, monkeypatch, base_state):
        captured = {}

        class BudgetSpy:
            def __init__(self, llm):
                pass

            async def run(self, payload):
                captured.update(payload)
                return {
                    "final_plan": {"daily_itinerary": [], "budget": {"details": []}},
                    "should_retry": False,
                    "adjusted_params": {},
                    "retry_count": 0,
                }

        monkeypatch.setattr("app.orchestrator.nodes.BudgetAgent", BudgetSpy)
        base_state["budget_no_limit"] = True
        base_state["preferences_provided"] = False

        from app.orchestrator.nodes import node_budget
        await node_budget(base_state)

        assert captured["budget_no_limit"] is True
        assert captured["preferences_provided"] is False
        assert captured["start_date"] == "2099-08-01"
        assert captured["end_date"] == "2099-08-03"
        assert captured["pace"] == "适中"
        assert captured["hotel_star"] == 4
        assert captured["hotel_budget"] == 500
        assert captured["meal_budget"] == 100
        assert captured["cuisine_preferences"] == ["川菜"]
        assert captured["preferred_transport"] == "地铁"

    @pytest.mark.asyncio
    async def test_budget_retry_preserves_dates_and_unadjusted_config(self, monkeypatch, base_state):
        captured = []

        class BudgetSpy:
            def __init__(self, llm):
                pass

            async def run(self, payload):
                captured.append(dict(payload))
                should_retry = len(captured) == 1
                return {
                    "final_plan": {"daily_itinerary": [], "budget": {"details": []}},
                    "should_retry": should_retry,
                    "adjusted_params": {"hotel_budget": 300} if should_retry else {},
                    "retry_count": len(captured),
                }

        monkeypatch.setattr("app.orchestrator.nodes.BudgetAgent", BudgetSpy)

        from app.orchestrator.nodes import node_adjust_params, node_budget

        first_result = await node_budget(base_state)
        retry_state = {**base_state, **first_result}
        retry_state.update(await node_adjust_params(retry_state))
        await node_budget(retry_state)

        assert [payload["start_date"] for payload in captured] == [
            "2099-08-01", "2099-08-01",
        ]
        assert [payload["end_date"] for payload in captured] == [
            "2099-08-03", "2099-08-03",
        ]
        assert captured[0]["cuisine_preferences"] == captured[1]["cuisine_preferences"]
        assert captured[0]["preferred_transport"] == captured[1]["preferred_transport"]
        assert captured[1]["hotel_budget"] == 300


# ═══════════════════════════════════════════════════════
# node_adjust_params / route_after_budget
# ═══════════════════════════════════════════════════════

class TestNodeAdjustParams:
    @pytest.mark.asyncio
    async def test_applies_adjusted_params(self, base_state):
        base_state["adjusted_params"] = {"hotel_budget": 300, "meal_budget": 60}
        base_state["retry_count"] = 1

        from app.orchestrator.nodes import node_adjust_params
        result = await node_adjust_params(base_state)
        assert result["hotel_budget"] == 300
        assert result.get("hotel_star") is None  # 未调整，key 不在 result 中
        assert result["meal_budget"] == 60

    @pytest.mark.asyncio
    async def test_empty_adjusted_params(self, base_state):
        from app.orchestrator.nodes import node_adjust_params
        result = await node_adjust_params(base_state)
        assert result["retry_count"] == 0


class TestRouteAfterBudget:
    def test_should_retry(self):
        from app.orchestrator.nodes import route_after_budget
        result = route_after_budget({"should_retry": True})
        assert result == "retry"

    def test_done(self):
        from app.orchestrator.nodes import route_after_budget
        result = route_after_budget({"should_retry": False})
        assert result == "done"
