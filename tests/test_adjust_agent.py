"""测试 app/agents/adjust_agent.py — AdjustAgent"""

import pytest
from tests.test_llm import MockLLM
from app.agents.adjust_agent import AdjustAgent


@pytest.fixture
def agent():
    return AdjustAgent(MockLLM(api_key="test", base_url="http://test", model="test"))


# ═══════════════════════════════════════════════════════
# run 派发
# ═══════════════════════════════════════════════════════

class TestRunDispatch:
    @pytest.mark.asyncio
    async def test_dispatches_to_weather(self, agent, monkeypatch):
        async def fake_handle(data):
            return {"dispatched": "weather", "data": data}
        monkeypatch.setattr(agent, "handle_weather", fake_handle)
        result = await agent.run({"trigger_type": "weather", "destination": "北京"})
        assert result["dispatched"] == "weather"

    @pytest.mark.asyncio
    async def test_dispatches_to_time_drift(self, agent, monkeypatch):
        async def fake_handle(data):
            return {"dispatched": "time_drift"}
        monkeypatch.setattr(agent, "handle_time_drift", fake_handle)
        result = await agent.run({"trigger_type": "time_drift"})
        assert result["dispatched"] == "time_drift"

    @pytest.mark.asyncio
    async def test_dispatches_to_budget_alert(self, agent, monkeypatch):
        async def fake_handle(data):
            return {"dispatched": "budget_alert"}
        monkeypatch.setattr(agent, "handle_budget_alert", fake_handle)
        result = await agent.run({"trigger_type": "budget_alert"})
        assert result["dispatched"] == "budget_alert"

    @pytest.mark.asyncio
    async def test_dispatches_to_user_request(self, agent, monkeypatch):
        async def fake_handle(data):
            return {"dispatched": "user_request"}
        monkeypatch.setattr(agent, "handle_user_request", fake_handle)
        result = await agent.run({"trigger_type": "user_request"})
        assert result["dispatched"] == "user_request"

    @pytest.mark.asyncio
    async def test_unknown_trigger_returns_error(self, agent):
        result = await agent.run({"trigger_type": "unknown_xyz"})
        assert "error" in result
        assert "Unknown trigger" in result["error"]


# ═══════════════════════════════════════════════════════
# handle_budget_alert
# ═══════════════════════════════════════════════════════

class TestHandleBudgetAlert:
    @pytest.mark.asyncio
    async def test_calculates_overage_and_generates_suggestions(self, agent):
        result = await agent.handle_budget_alert({
            "budget_spent": 1200,
            "budget_total": 1000,
            "remaining_days": 3,
        })
        assert result["trigger_type"] == "budget_alert"
        assert result["trigger_detail"]["over_pct"] == 20.0
        assert len(result["suggestions"]) >= 3
        assert result["requires_confirmation"] is False

    @pytest.mark.asyncio
    async def test_under_budget_no_specific_restriction(self, agent):
        result = await agent.handle_budget_alert({
            "budget_spent": 500,
            "budget_total": 2000,
            "remaining_days": 5,
        })
        # over_pct 为负 — 未超预算
        assert result["trigger_detail"]["over_pct"] < 0

    @pytest.mark.asyncio
    async def test_zero_days_remaining_handled(self, agent):
        result = await agent.handle_budget_alert({
            "budget_spent": 1000,
            "budget_total": 800,
            "remaining_days": 0,
        })
        assert "trigger_type" in result


# ═══════════════════════════════════════════════════════
# handle_time_drift
# ═══════════════════════════════════════════════════════

class TestHandleTimeDrift:
    @pytest.mark.asyncio
    async def test_on_time_returns_no_adjustment(self, agent):
        result = await agent.handle_time_drift({
            "drift_min": -5,  # 提前了
            "current_day": 1,
        })
        assert "no adjustment" in result["reason"]

    @pytest.mark.asyncio
    async def test_zero_drift_no_adjustment(self, agent):
        result = await agent.handle_time_drift({
            "drift_min": 0,
            "current_day": 1,
        })
        assert "no adjustment" in result["reason"]

    @pytest.mark.asyncio
    async def test_behind_schedule_compresses(self, agent):
        result = await agent.handle_time_drift({
            "drift_min": 45,
            "current_day": 1,
            "remaining_stops": [
                {"name": "低评分", "rating": 3.0, "duration_h": 2, "type": "attraction"},
                {"name": "高评分", "rating": 4.8, "duration_h": 1.5},
                {"name": "一般般", "rating": 3.5, "duration_h": 1},
            ],
        })
        assert result["trigger_type"] == "time_drift"
        assert result["requires_confirmation"] is True


# ═══════════════════════════════════════════════════════
# 纯同步 helpers
# ═══════════════════════════════════════════════════════

class TestFindOutdoorAttractions:
    def test_filters_by_tags(self, agent):
        day_data = {"attractions": [
            {"name": "登山公园", "tags": ["登山", "公园"]},
            {"name": "博物馆", "tags": ["博物馆"]},
            {"name": "海滩", "tags": "海滩;游泳"},  # str tags
        ]}
        result = agent._find_outdoor_attractions(day_data, "暴雨")
        assert len(result) == 2  # 登山公园 + 海滩
        assert result[0]["name"] == "登山公园"
        assert result[1]["name"] == "海滩"

    def test_irrelevant_weather_returns_empty(self, agent):
        day_data = {"attractions": [{"name": "登山", "tags": ["户外"]}]}
        result = agent._find_outdoor_attractions(day_data, "多云")
        assert result == []

    def test_empty_attractions_returns_empty(self, agent):
        result = agent._find_outdoor_attractions({"attractions": []}, "暴雨")
        assert result == []

    def test_category_match(self, agent):
        day_data = {"attractions": [
            {"name": "桂林公园", "category": "公园", "tags": []},
        ]}
        result = agent._find_outdoor_attractions(day_data, "高温")
        assert len(result) == 1


class TestCompressStops:
    def test_removes_low_rating_and_compresses_others(self, agent):
        stops = [
            {"name": "无聊景点", "rating": 3.0, "duration_h": 2, "type": "attraction"},
            {"name": "热门景点", "rating": 4.5, "duration_h": 2},
            {"name": "一般景点", "rating": 3.5, "duration_h": 1},
        ]
        # drift_min=100: 第一个低评分景点被砍节省 120 分钟，已经 >= 100
        # 所以剩下两个直接保留，不压缩
        adjusted, removed = agent._compress_stops(stops, drift_min=100)
        assert len(removed) == 1
        assert removed[0]["name"] == "无聊景点"
        assert len(adjusted) == 2
        # 后面两个未被压缩（因为已经省够时间）
        names = [a["name"] for a in adjusted]
        assert "热门景点" in names
        assert "一般景点" in names

    def test_empty_stops(self, agent):
        adjusted, removed = agent._compress_stops([], 30)
        assert adjusted == []
        assert removed == []

    def test_sufficient_saved_stops_early_exit(self, agent):
        stops = [
            {"name": "低分", "rating": 3.0, "duration_h": 1, "type": "attraction"},
            {"name": "高分", "rating": 4.5, "duration_h": 1},
        ]
        adjusted, removed = agent._compress_stops(stops, drift_min=30)
        # 第一个低评分被砍节省 60 分钟，已经超过 30 分钟目标
        assert len(removed) == 1
        # 第二个直接保留
        assert len(adjusted) == 1
        assert adjusted[0]["name"] == "高分"


class TestWeatherSuggestion:
    def test_heavy_rain(self, agent):
        result = agent._weather_suggestion("暴雨", 3)
        assert "暴雨" in result
        assert "3个" in result

    def test_high_temp(self, agent):
        result = agent._weather_suggestion("高温", 2)
        assert "上午" in result

    def test_strong_wind(self, agent):
        result = agent._weather_suggestion("大风", 1)
        assert "大风" in result

    def test_unknown_weather_returns_empty(self, agent):
        assert agent._weather_suggestion("晴天", 1) == ""


class TestSummarizePlan:
    def test_multi_day_summary(self, agent):
        daily_plan = [
            {"day": 1, "attractions": [{"name": "故宫"}, {"name": "天坛"}]},
            {"day": 2, "attractions": [{"name": "长城"}]},
        ]
        result = agent._summarize_plan(daily_plan)
        assert "Day1" in result
        assert "故宫" in result
        assert "天坛" in result
        assert "Day2" in result
        assert "长城" in result

    def test_empty_plan(self, agent):
        assert agent._summarize_plan([]) == ""
        assert agent._summarize_plan(None) == ""


class TestApplyWeatherChanges:
    def test_replaces_outdoor_with_alternatives(self, agent):
        daily_plan = [
            {"day": 1, "attractions": [
                {"name": "户外公园", "tags": ["户外"]},
                {"name": "室内博物馆", "tags": ["博物馆"]},
            ]},
        ]
        adjustments = [{
            "day": 1,
            "affected_attractions": [{"name": "户外公园"}],
            "alternatives": [{"name": "科技馆", "reason": "室内替代", "tags": ["科技"]}],
        }]
        result = agent._apply_weather_changes(daily_plan, adjustments)
        # 户外公园被移除
        names = [a["name"] for a in result[0]["attractions"]]
        assert "户外公园" not in names
        assert "室内博物馆" in names
        assert "科技馆" in names


class TestExtractDaySections:
    def test_filters_by_day_list(self, agent):
        daily_plan = [
            {"day": 1, "data": "a"},
            {"day": 2, "data": "b"},
            {"day": 3, "data": "c"},
        ]
        result = agent._extract_day_sections(daily_plan, [1, 3])
        assert len(result) == 2
        assert result[0]["day"] == 1
        assert result[1]["day"] == 3


class TestWeatherReason:
    def test_formats_reason(self, agent):
        adjustments = [
            {"affected_attractions": [{"name": "a"}, {"name": "b"}]},
            {"affected_attractions": [{"name": "c"}]},
        ]
        result = agent._weather_reason("暴雨", adjustments)
        assert "暴雨" in result
        assert "3" in result


# ═══════════════════════════════════════════════════════
# handle_weather (mock _search_indoor_alternatives)
# ═══════════════════════════════════════════════════════

class TestHandleWeather:
    @pytest.mark.asyncio
    async def test_returns_adjustments(self, agent, monkeypatch):
        async def fake_search_indoor(self, city, affected, prefs):
            return [{"name": "室内博物馆", "reason": "替代"}]

        monkeypatch.setattr(AdjustAgent, "_search_indoor_alternatives", fake_search_indoor)

        result = await agent.handle_weather({
            "affected_days": [1],
            "weather_type": "暴雨",
            "destination": "北京",
            "daily_plan": [
                {"day": 1, "attractions": [
                    {"name": "长城", "tags": ["户外", "登山"]},
                ]},
            ],
            "preferences": ["文化"],
        })

        assert result["trigger_type"] == "weather"
        assert result["requires_confirmation"] is True
        assert len(result["adjustments"]) == 1
        assert result["adjustments"][0]["alternatives"][0]["name"] == "室内博物馆"


# ═══════════════════════════════════════════════════════
# handle_user_request (mock call_llm)
# ═══════════════════════════════════════════════════════

class TestHandleUserRequest:
    @pytest.mark.asyncio
    async def test_calls_llm_for_request(self, agent, monkeypatch):
        async def fake_call_llm(messages, temperature=0.7, max_retries=3):
            return "建议1: 换去颐和园。建议2: 删除上午的景点。建议3: 把第二天的行程提前。"

        monkeypatch.setattr(agent, "call_llm", fake_call_llm)

        result = await agent.handle_user_request({
            "request": "想去颐和园",
            "destination": "北京",
            "daily_plan": [{"day": 1, "attractions": [{"name": "天坛"}]}],
        })

        assert result["trigger_type"] == "user_request"
        assert result["requires_confirmation"] is True
        assert "颐和园" in result["reason"]

    @pytest.mark.asyncio
    async def test_llm_failure_returns_fallback(self, agent, monkeypatch):
        async def fake_failing_llm(messages, temperature=0.7, max_retries=3):
            raise RuntimeError("LLM down")

        monkeypatch.setattr(agent, "call_llm", fake_failing_llm)

        result = await agent.handle_user_request({
            "request": "换景点",
            "destination": "北京",
            "daily_plan": [],
        })

        assert result["trigger_type"] == "user_request"
        assert "收到调整请求" in result["reason"]
