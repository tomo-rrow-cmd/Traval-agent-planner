"""测试 app/agents/context.py — PlanContext 全局上下文"""

import pytest
from app.agents.context import PlanContext, ContextChangeLog


class TestPlanContextWrite:
    def test_write_increments_version(self):
        ctx = PlanContext()
        assert ctx.get_version() == 0
        ctx.write("destination", "北京", "UserAgent")
        assert ctx.get_version() == 1
        ctx.write("budget", 5000, "UserAgent")
        assert ctx.get_version() == 2

    def test_write_creates_change_log_entry(self):
        ctx = PlanContext()
        ctx.write("destination", "北京", "UserAgent", "设置目的地")
        assert len(ctx.change_log) == 1
        log = ctx.change_log[0]
        assert log.version == 1
        assert log.field_name == "destination"
        assert log.agent_name == "UserAgent"
        assert log.summary == "设置目的地"

    def test_write_sets_field_value(self):
        ctx = PlanContext()
        ctx.write("destination", "云南昆明", "UserAgent")
        assert ctx.destination == "云南昆明"

    def test_write_unknown_field_raises_attribute_error(self):
        ctx = PlanContext()
        with pytest.raises(AttributeError, match="不存在字段"):
            ctx.write("nonexistent_field", "value", "TestAgent")

    def test_write_default_summary(self):
        ctx = PlanContext()
        ctx.write("budget", 3000, "BudgetAgent")
        assert "BudgetAgent" in ctx.change_log[0].summary
        assert "budget" in ctx.change_log[0].summary

    def test_change_log_capped_at_100_entries(self):
        ctx = PlanContext()
        for i in range(150):
            ctx.write("destination", f"city-{i}", "UserAgent")
        assert len(ctx.change_log) == 100
        # 最老的条目应该被移除（保留最近100条）
        assert ctx.change_log[0].field_name == "destination"
        versions = [log.version for log in ctx.change_log]
        assert min(versions) == 51  # 前50条被裁剪
        assert ctx.get_version() == 150


class TestPlanContextGetVersion:
    def test_initial_version_is_zero(self):
        ctx = PlanContext()
        assert ctx.get_version() == 0

    def test_version_after_multiple_writes(self):
        ctx = PlanContext()
        for i in range(5):
            ctx.write("budget", i * 1000, "Test")
        assert ctx.get_version() == 5


class TestPlanContextGetOwnerAgent:
    def test_known_field_returns_owner(self):
        ctx = PlanContext()
        assert ctx.get_owner_agent("weather_data") == "WeatherAgent"
        assert ctx.get_owner_agent("attractions") == "AttractionAgent"
        assert ctx.get_owner_agent("restaurants") == "FoodAgent"
        assert ctx.get_owner_agent("hotels") == "HotelAgent"
        assert ctx.get_owner_agent("traffic_plan") == "TrafficAgent"
        assert ctx.get_owner_agent("daily_itinerary") == "RouteOptimizerAgent"
        assert ctx.get_owner_agent("total_cost") == "BudgetAgent"
        assert ctx.get_owner_agent("souvenirs") == "SouvenirAgent"

    def test_unknown_field_returns_none(self):
        ctx = PlanContext()
        assert ctx.get_owner_agent("destination") is None
        assert ctx.get_owner_agent("user_id") is None
        assert ctx.get_owner_agent("nonexistent") is None


class TestPlanContextToDict:
    def test_default_context_dict(self):
        ctx = PlanContext()
        d = ctx.to_dict()
        assert d["user_id"] == ""
        assert d["destination"] == ""
        assert d["start_date"] is None
        assert d["end_date"] is None
        assert d["budget"] == 0.0
        assert d["travelers"] == 1
        assert d["context_version"] == 0

    def test_populated_context_dict(self):
        ctx = PlanContext(destination="北京", budget=5000, travelers=2)
        ctx.write("attractions", [{"name": "故宫"}], "AttractionAgent")
        d = ctx.to_dict()
        assert d["destination"] == "北京"
        assert d["budget"] == 5000
        assert d["travelers"] == 2
        assert d["attractions"] == [{"name": "故宫"}]
        assert d["context_version"] == 1

    def test_dict_includes_all_required_keys(self):
        ctx = PlanContext()
        d = ctx.to_dict()
        expected_keys = {
            "user_id", "destination", "start_date", "end_date", "budget",
            "travelers", "preferences", "weather_data", "attractions",
            "restaurants", "hotels", "traffic_plan", "daily_itinerary",
            "total_cost", "souvenirs", "context_version",
        }
        assert set(d.keys()) >= expected_keys


class TestPlanContextErrors:
    def test_add_error_appends_to_list(self):
        ctx = PlanContext()
        ctx.add_error("天气数据获取失败")
        ctx.add_error("酒店搜索超时")
        assert ctx.errors == ["天气数据获取失败", "酒店搜索超时"]

    def test_errors_start_empty(self):
        ctx = PlanContext()
        assert ctx.errors == []


class TestPlanContextUpdateStage:
    def test_update_stage_changes_current_stage(self):
        ctx = PlanContext()
        assert ctx.current_stage == "init"
        ctx.update_stage("planning")
        assert ctx.current_stage == "planning"
        ctx.update_stage("confirmed")
        assert ctx.current_stage == "confirmed"


class TestContextChangeLog:
    def test_dataclass_fields(self):
        log = ContextChangeLog(
            version=1,
            field_name="destination",
            agent_name="UserAgent",
            timestamp="2026-07-14T10:00:00",
            summary="设置目的地为北京",
        )
        assert log.version == 1
        assert log.field_name == "destination"
        assert log.agent_name == "UserAgent"
        assert log.timestamp == "2026-07-14T10:00:00"
        assert log.summary == "设置目的地为北京"
