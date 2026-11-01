"""
LangGraph Nodes — 文档 §4 五阶段节点

阶段1: plan_attraction + plan_food + plan_hotel (并行)
阶段2: decision (方案决策)
阶段3: plan_traffic (交通)
阶段4: plan_budget (预算+最终输出)
"""

import asyncio
import re
from datetime import date as dt_date, timedelta
from typing import Any

from app.agents.attraction_agent import AttractionAgent
from app.agents.budget_agent import BudgetAgent
from app.agents.decision_agent import DecisionAgent
from app.agents.food_agent import FoodAgent
from app.agents.hotel_agent import HotelAgent
from app.agents.traffic_agent import TrafficAgent
from app.orchestrator.state import PlannerState
from app.services.llm.deepseek import DeepSeekLLM

llm = DeepSeekLLM()


async def node_weather(state: PlannerState) -> dict[str, Any]:
    """阶段0: 天气预取 — 拉取目的地预报并计算影响因子"""
    destination = state.get("destination", "")
    days = state.get("days", 2)
    preferred_transport = state.get("preferred_transport", "transit")

    start_date = state.get("start_date", "")
    end_date = state.get("end_date", "")

    from app.agents.weather_agent import WeatherAgent
    from app.services.weather.impact import build_neutral_impacts

    weather_status = "fallback"
    try:
        agent = WeatherAgent(llm)
        result = await agent.generate_impact_factors(
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            days=days,
            preferred_transport=preferred_transport,
        )
        weather_forecast = result.get("forecasts", [])
        weather_impact = result.get("impacts", [])
        if weather_forecast:
            weather_status = "success"
    except Exception as e:
        print(f"  [Weather] 获取失败，使用中性影响: {e}")
        weather_forecast = []
        weather_impact = build_neutral_impacts(
            days=days,
            start_date=start_date,
            preferred_transport=preferred_transport,
        )

    # 为每个 forecast 预计算 summary 字段，方便下游直接使用
    for fc in weather_forecast:
        if "summary" not in fc:
            day_w = fc.get("dayweather", "")
            night_w = fc.get("nightweather", "")
            day_t = fc.get("daytemp", "")
            night_t = fc.get("nighttemp", "")
            weather_text = day_w or night_w or "?"
            fc["summary"] = f"{weather_text} {day_t}°C / {night_t}°C"

    return {
        "weather_forecast": weather_forecast,
        "weather_impact": weather_impact,
        "weather_status": weather_status,
        "current_stage": "fetch_weather",
    }


def _dedupe_daily_plan(daily_plan: list[dict]) -> list[dict]:
    cleaned = []
    for day in daily_plan or []:
        seen = set()
        attractions = []
        for attraction in day.get("attractions", []):
            name_key = _normalize_attraction_name(attraction.get("name", ""))
            if name_key and name_key in seen:
                continue
            if name_key:
                seen.add(name_key)
            attractions.append(attraction)
        cleaned_day = dict(day)
        cleaned_day["attractions"] = attractions
        cleaned.append(cleaned_day)
    return cleaned


def _normalize_attraction_name(name: str) -> str:
    text = str(name or "").replace("（", "(").replace("）", ")")
    text = text.split("(", 1)[0]
    return re.sub(r"\s+", "", text).lower()


async def node_parallel_planning(state: PlannerState) -> dict[str, Any]:
    """阶段2: 景点+美食+酒店 并行规划"""
    dest = state.get("destination", "")
    days = state.get("days", 2)
    prefs = state.get("preferences", [])
    pace = state.get("pace", "适中")
    hotel_star = state.get("hotel_star", 3)
    hotel_budget = state.get("hotel_budget", 500)
    meal_budget = state.get("meal_budget", 100)
    cuisine_preferences = state.get("cuisine_preferences", [])

    weather_impact = state.get("weather_impact", [])

    attr_t = AttractionAgent(llm).run({
        "destination": dest, "days": days, "preferences": prefs, "pace": pace,
        "weather_impact": weather_impact,
    })
    food_t = FoodAgent(llm).run({
        "destination": dest, "days": days, "meal_budget": meal_budget,
        "cuisine_preferences": cuisine_preferences,
    })
    hotel_t = HotelAgent(llm).run({
        "destination": dest, "days": days,
        "hotel_star_min": hotel_star, "budget_per_night": hotel_budget,
    })

    attr, food, hotel = await asyncio.gather(attr_t, food_t, hotel_t)
    daily_plan = _dedupe_daily_plan(attr.get("daily_plan", []))
    return {
        "daily_plan": daily_plan,
        "meal_plan": food.get("meal_plan", []),
        "hotel_plan": hotel.get("hotel_plan", {}),
        "meituan_hotels": hotel.get("meituan_hotels", []),
        "current_stage": "parallel_planning",
    }


async def node_decision_r1(state: PlannerState) -> dict[str, Any]:
    """阶段3-R1: 定稿景点+餐厅（不含酒店）"""
    dec = await DecisionAgent(llm).run_round1({
        "daily_plan": state.get("daily_plan", []),
        "meal_plan": state.get("meal_plan", []),
    })
    dp = _dedupe_daily_plan(dec.get("daily_plan", state.get("daily_plan", [])) or [])
    return {
        "daily_plan": dp,
        "meal_plan": dec.get("meal_plan", state.get("meal_plan", [])),
        "current_stage": "decision_r1",
    }


async def node_decision_r2(state: PlannerState) -> dict[str, Any]:
    """阶段3-R2: 交通评估后选最优酒店"""
    dec = await DecisionAgent(llm).run_round2({
        "hotel_plan": state.get("hotel_plan", {}),
        "daily_plan": state.get("daily_plan", []),
        "destination": state.get("destination", ""),
    })
    return {
        "hotel_plan": dec.get("hotel_plan", state.get("hotel_plan", {})),
        "current_stage": "decision_r2",
    }


async def node_detail_enrich(state: PlannerState) -> dict[str, Any]:
    """决策后深度扩展：挑亮点景点/餐厅获取详情"""
    from app.agents.detail_agent import DetailAgent

    detail = await DetailAgent(llm).run({
        "daily_plan": state.get("daily_plan", []),
        "meal_plan": state.get("meal_plan", []),
        "destination": state.get("destination", ""),
    })
    return {
        "attraction_details": detail.get("attraction_details", []),
        "food_details": detail.get("food_details", []),
        "current_stage": "detail_enrich",
    }


async def node_traffic(state: PlannerState) -> dict[str, Any]:
    """阶段4: 交通规划（高德闭环+12306大交通+时间约束）"""
    dest = state.get("destination", "")
    origin = state.get("origin", "")
    daily = state.get("daily_plan", [])

    traffic = await TrafficAgent(llm).run({
        "destination": dest, "days": len(daily),
        "start_date": state.get("start_date", ""),
        "end_date": state.get("end_date", ""),
        "daily_locations": daily, "origin": origin,
        "meal_plan": state.get("meal_plan", []),
        "hotel_plan": state.get("hotel_plan", {}),
        "preferred_transport": state.get("preferred_transport", "地铁"),
        "weather_impact": state.get("weather_impact", []),
    })

    return {
        "traffic": traffic,
        "big_traffic": traffic.get("big_traffic", {}),
        "time_warnings": traffic.get("time_warnings", []),
        "current_stage": "traffic",
    }


async def node_budget(state: PlannerState) -> dict[str, Any]:
    """阶段5: 预算核算 + 最终方案输出"""
    daily = state.get("daily_plan", [])
    meals = state.get("meal_plan", [])
    hotels = state.get("hotel_plan", {})
    traffic = state.get("traffic", {})

    attr_cost = sum(a.get("price", 0) for d in daily for a in d.get("attractions", []))
    meal_cost = sum(m.get("avg_price", 0) for d in meals for m in d.get("meals", []))
    recommendations = hotels.get("recommendations", [])
    selected_name = hotels.get("selected")
    selected_hotel = hotels.get("selected_hotel")
    if not selected_hotel and selected_name:
        selected_hotel = next(
            (hotel for hotel in recommendations if hotel.get("name") == selected_name),
            None,
        )
    if not selected_hotel and len(recommendations) == 1:
        selected_hotel = recommendations[0]
    hotel_cost = (selected_hotel or {}).get("total", 0)
    traf_cost = traffic.get("total_traffic_cost", 0)

    result = await BudgetAgent(llm).run({
        "total_budget": state.get("total_budget", 5000),
        "reserve_budget": state.get("reserve_budget", 0),
        "planning_budget": state.get("planning_budget", state.get("total_budget", 5000)),
        "days": state.get("days", 2),
        "start_date": state.get("start_date", ""),
        "end_date": state.get("end_date", ""),
        "travelers": state.get("travelers", 1),
        "destination": state.get("destination", ""),
        "origin": state.get("origin", ""),
        "preferences": state.get("preferences", []),
        "preferences_provided": state.get("preferences_provided", True),
        "budget_no_limit": state.get("budget_no_limit", False),
        "pace": state.get("pace", "适中"),
        "hotel_star": state.get("hotel_star", 3),
        "hotel_budget": state.get("hotel_budget", 500),
        "meal_budget": state.get("meal_budget", 100),
        "cuisine_preferences": state.get("cuisine_preferences", []),
        "preferred_transport": state.get("preferred_transport", "地铁"),
        "expenses": {"hotels": hotel_cost, "traffic": traf_cost,
                     "meals": meal_cost, "attractions": attr_cost},
        "daily_itinerary": daily,
        "meal_plan": meals,
        "hotel_plan": hotels,
        "traffic": traffic,
        "big_traffic": state.get("big_traffic", {}),
        "meituan_hotels": state.get("meituan_hotels", []),
        "attraction_details": state.get("attraction_details", []),
        "food_details": state.get("food_details", []),
        "retry_count": state.get("retry_count", 0),
        "adjusted_params": state.get("adjusted_params", {}),
    })

    # 标记无数据的类目（spent=0 但 budget>0）
    final_plan = result.get("final_plan", {})
    budget_detail = final_plan.get("budget", {})
    for d in budget_detail.get("details", []):
        if d.get("spent", 0) == 0 and d.get("budget", 0) > 0 and d.get("status") == "ok":
            d["status"] = "no_data"
            d["note"] = "暂无该类别数据"

    # ---- 天气注入：为 daily_itinerary 每天填充 weather_summary ----
    weather_forecast = state.get("weather_forecast", [])
    weather_impact = state.get("weather_impact", [])
    weather_status = state.get("weather_status", "fallback")
    daily_itinerary = final_plan.get("daily_itinerary", [])

    start_date = state.get("start_date", "")
    end_date = state.get("end_date", "")
    final_plan["start_date"] = start_date
    final_plan["end_date"] = end_date
    final_plan["days"] = state.get("days", len(daily_itinerary))
    final_plan["cuisine_preferences"] = state.get("cuisine_preferences", [])
    final_plan["preferred_transport"] = state.get("preferred_transport", "地铁")
    final_plan["preferred_transport_provided"] = state.get(
        "preferred_transport_provided",
        False,
    )
    trip_config = final_plan.setdefault("trip_config", {})
    trip_config.update({
        "start_date": start_date,
        "end_date": end_date,
        "days": state.get("days", len(daily_itinerary)),
        "cuisine_preferences": state.get("cuisine_preferences", []),
        "preferred_transport": state.get("preferred_transport", "地铁"),
        "preferred_transport_provided": state.get(
            "preferred_transport_provided",
            False,
        ),
    })

    try:
        trip_start = dt_date.fromisoformat(start_date)
    except (TypeError, ValueError):
        trip_start = None

    forecast_by_date = {
        forecast.get("date"): forecast
        for forecast in weather_forecast
        if forecast.get("date")
    }
    impact_by_date = {
        impact.get("date"): impact
        for impact in weather_impact
        if impact.get("date")
    }

    for day_index, day in enumerate(daily_itinerary):
        if trip_start:
            itinerary_date = trip_start + timedelta(days=day_index)
            day["date"] = itinerary_date.isoformat()
            day["date_label"] = f"{itinerary_date.month}月{itinerary_date.day}日"

        # 如果后端 LLM 已经填了 weather_summary 就保留，否则按日期关联天气
        if not day.get("weather_summary"):
            fc = forecast_by_date.get(day.get("date"))
            wi = impact_by_date.get(day.get("date"))
            if fc:
                day["weather_summary"] = fc.get("summary") or f"{fc.get('dayweather','')} {fc.get('daytemp','')}°C / {fc.get('nighttemp','')}°C"
            elif wi:
                day["weather_summary"] = f"{wi.get('dayweather','?')} {wi.get('daytemp','')}°C / {wi.get('nighttemp','')}°C"

    final_plan["daily_itinerary"] = daily_itinerary
    final_plan["daily_plan"] = daily_itinerary

    final_plan["weather_forecast"] = weather_forecast
    final_plan["weather_impact"] = weather_impact
    final_plan["weather_status"] = weather_status

    # ---- 大交通注入：确保去程+返程火车票都在 final_plan 中 ----
    bt = state.get("big_traffic", {})
    if bt:
        final_plan["big_traffic"] = bt

    return {
        "final_plan": result.get("final_plan", {}),
        "should_retry": result.get("should_retry", False),
        "adjusted_params": result.get("adjusted_params", {}),
        "retry_count": result.get("retry_count", 0),
        "current_stage": "completed",
    }


async def node_adjust_params(state: PlannerState) -> dict[str, Any]:
    """将修正参数写入状态，降低预算重跑并行规划"""
    adj = state.get("adjusted_params", {})
    updates = {"retry_count": state.get("retry_count", 0)}
    if adj.get("hotel_budget"):
        updates["hotel_budget"] = adj["hotel_budget"]
    if adj.get("hotel_star"):
        updates["hotel_star"] = adj["hotel_star"]
    if adj.get("meal_budget"):
        updates["meal_budget"] = adj["meal_budget"]
    return updates


def route_after_budget(state: PlannerState) -> str:
    """预算后路由：OK→结束, 轻超→自动调参重跑, 严重→结束"""
    if state.get("should_retry"):
        return "retry"
    return "done"
