"""测试 run_pipeline 初始状态字段透传。"""

import pytest


@pytest.mark.asyncio
async def test_pipeline_initial_state_preserves_agent_fields(monkeypatch):
    from app.orchestrator import pipeline as pipeline_module

    captured = {}

    class FakeGraph:
        async def astream(self, initial, stream_mode="updates"):
            captured.update(initial)
            yield {"budget": {"final_plan": {}, "current_stage": "completed"}}

    monkeypatch.setattr(pipeline_module, "planner_graph", FakeGraph())

    events = []
    async for event in pipeline_module.run_pipeline({
        "confirmed": True,
        "destination": "北京",
        "start_date": "2099-08-01",
        "end_date": "2099-08-03",
        "days": 3,
        "preferred_transport": "步行",
        "cuisine_preferences": "川菜，粤菜，川菜",
        "budget_no_limit": True,
        "preferences_provided": False,
    }):
        events.append(event)

    assert events[-1][0] == "done"
    assert captured["start_date"] == "2099-08-01"
    assert captured["end_date"] == "2099-08-03"
    assert captured["days"] == 3
    assert captured["preferred_transport"] == "步行"
    assert captured["cuisine_preferences"] == ["川菜", "粤菜"]
    assert captured["budget_no_limit"] is True
    assert captured["preferences_provided"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize(("params", "error_code"), [
    ({"days": 3}, "missing_start_date"),
    ({"start_date": "2099-08-01", "end_date": "2099-08-03", "days": 2}, "date_days_conflict"),
    ({"start_date": "2099-08-03", "end_date": "2099-08-01"}, "end_before_start"),
    ({"start_date": "not-a-date", "days": 3}, "invalid_format"),
    ({"start_date": "2000-01-01", "days": 3}, "past_start_date"),
])
async def test_pipeline_invalid_dates_do_not_start_graph(monkeypatch, params, error_code):
    from app.orchestrator import pipeline as pipeline_module

    class ForbiddenGraph:
        async def astream(self, initial, stream_mode="updates"):
            raise AssertionError("invalid dates must not start LangGraph")
            yield initial, stream_mode

    monkeypatch.setattr(pipeline_module, "planner_graph", ForbiddenGraph())

    events = []
    async for event in pipeline_module.run_pipeline({"confirmed": True, **params}):
        events.append(event)

    assert events == [("error", {
        "error_code": error_code,
        "message": events[0][1]["message"],
    })]
