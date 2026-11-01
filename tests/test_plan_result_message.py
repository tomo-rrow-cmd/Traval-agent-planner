from app.services.application.plan_result_message import build_plan_result_message


def test_build_plan_result_message_uses_three_line_summary():
    summary = {
        "destination": "北京",
        "origin": "武汉",
        "days": 3,
        "trip_config": {"travelers": 1},
        "budget": {"actual_total": 1349, "total_budget": 3000},
        "daily_itinerary": [{"day": 1, "attractions": [{"name": "故宫"}]}],
        "weather_forecast": [{"weather": "晴"}],
        "traffic": {"summary": "市内交通约20小时"},
    }

    result = build_plan_result_message(summary)

    assert result == (
        "✅ 北京3日方案已生成\n"
        "武汉 → 北京 · 3天 · 1人\n"
        "预计 ¥1349 / 预算 ¥3000"
    )
    assert "故宫" not in result
    assert "天气" not in result
    assert "交通" not in result


def test_build_plan_result_message_omits_missing_values():
    assert build_plan_result_message({"destination": "上海"}) == (
        "✅ 上海旅行方案已生成\n上海"
    )
    assert build_plan_result_message({}) == "✅ 旅行方案已生成"


def test_build_plan_result_message_uses_root_budget_fallback():
    result = build_plan_result_message({
        "destination": "杭州",
        "days": "2",
        "people_count": 2,
        "estimated_cost": 1288.5,
        "total_budget": 2500,
    })

    assert result == (
        "✅ 杭州2日方案已生成\n"
        "杭州 · 2天 · 2人\n"
        "预计 ¥1288.5 / 预算 ¥2500"
    )
