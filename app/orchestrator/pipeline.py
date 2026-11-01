"""
LangGraph 规划管线 — 文档 §4 五阶段

用法:
    async for event, data in run_pipeline(params):
        yield (event, data)
"""

import asyncio
import json
import re
from datetime import date, datetime, timedelta
from typing import Any, AsyncIterator
from zoneinfo import ZoneInfo

from app.orchestrator.graph import planner_graph
from app.orchestrator.state import PlannerState
from app.services.llm.deepseek import DeepSeekLLM
from app.utils.validator import resolve_trip_dates


def _normalize_cuisine_preferences(value: Any) -> list[str]:
    if isinstance(value, str):
        values = re.split(r"[,，、/；;\s]+", value)
    elif isinstance(value, list):
        values = value
    else:
        values = []

    normalized = []
    for value_item in values:
        item = str(value_item).strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def _normalize_transport(value: Any) -> str:
    text = re.sub(r"\s+", "", str(value or "")).lower()
    if any(term in text for term in ("步行", "走路", "徒步", "walking", "walk")):
        return "步行"
    if any(term in text for term in ("打车", "出租", "网约车", "taxi", "叫车")):
        return "打车"
    if any(term in text for term in ("自驾", "开车", "driving", "drive")):
        return "自驾"
    return "地铁"


async def run_pipeline(params: dict) -> AsyncIterator[tuple[str, dict]]:
    """LangGraph 五阶段 → SSE 事件流"""

    if not params.get("confirmed"):
        yield ("done", {
            "status": "waiting_confirmation",
            "message": "confirmation_required",
        })
        return

    date_result = resolve_trip_dates(
        params.get("start_date"),
        params.get("end_date"),
        params.get("days"),
        today=datetime.now(ZoneInfo("Asia/Shanghai")).date(),
    )
    if not date_result.get("ok"):
        yield ("error", {
            "error_code": date_result.get("error_code", "invalid_trip_dates"),
            "message": date_result.get("message", "旅行日期无效"),
        })
        return

    total_budget = float(params.get("total_budget") or 5000)
    reserve_budget = float(params.get("reserve_budget") or 0)
    planning_budget = float(
        params.get("planning_budget")
        or max(total_budget - reserve_budget, 0)
        or total_budget
    )
    initial: PlannerState = {
        "destination": params.get("destination", ""),
        "origin": params.get("origin", ""),
        "start_date": date_result["start_date"],
        "end_date": date_result["end_date"],
        "days": date_result["days"],
        "total_budget": total_budget,
        "reserve_budget": reserve_budget,
        "planning_budget": planning_budget,
        "budget_no_limit": bool(params.get("budget_no_limit", False)),
        "preferences": params.get("preferences", []),
        "preferences_provided": bool(params.get("preferences_provided", True)),
        "cuisine_preferences": _normalize_cuisine_preferences(
            params.get("cuisine_preferences", []),
        ),
        "pace": params.get("pace", "适中"),
        "hotel_star": params.get("hotel_star", 3),
        "hotel_budget": params.get("hotel_budget", 500),
        "meal_budget": params.get("meal_budget", 100),
        "travelers": params.get("travelers", 1),
        "preferred_transport": _normalize_transport(
            params.get("preferred_transport", "地铁"),
        ),
        "preferred_transport_provided": bool(
            params.get("preferred_transport_provided", False),
        ),
        "retry_count": 0,
        "adjusted_params": {},
        "should_retry": False,
    }

    yield ("step_start", {"step": "planning", "label": f"规划 {initial.get('destination','')} {initial.get('days',0)}天行程..."})

    stage_progress = {
        "fetch_weather": (3, "查询天气中..."),
        "parallel_planning": (18, "并行规划行程中..."),
        "decision_r1": (33, "决策R1：景点+餐饮..."),
        "detail_enrich": (48, "深度挖掘景点详情..."),
        "decision_r2": (63, "决策R2：精选酒店..."),
        "plan_traffic": (75, "规划市内交通..."),
        "traffic": (75, "规划市内交通..."),
        "budget": (92, "预算分析+生成方案..."),
        "completed": (100, "完成"),
    }

    try:
        final_state: PlannerState = dict(initial)

        async for update in planner_graph.astream(initial, stream_mode="updates"):
            if not isinstance(update, dict):
                continue

            for node_name, node_update in update.items():
                if not isinstance(node_update, dict):
                    continue

                final_state.update(node_update)
                stage = node_update.get("current_stage") or node_name
                percent, message = stage_progress.get(
                    stage,
                    stage_progress.get(node_name, (90, f"{stage}...")),
                )
                yield ("progress", {
                    "step": stage,
                    "percent": percent,
                    "message": message,
                })

        summary = final_state.get("final_plan", {})
        if isinstance(summary, dict) and "daily_itinerary" in summary and "daily_plan" not in summary:
            summary = {**summary, "daily_plan": summary["daily_itinerary"]}

        # LLM 回退：当天气/餐饮数据为空时调用 DeepSeek 生成
        await _llm_fallback(summary)

        # 标准化 summary 字段：把后端格式转为前端 PlanResponse 期望的格式
        summary = _normalize_summary(summary)

        yield ("done", {
            "summary": summary,
            "retry_count": final_state.get("retry_count", 0),
            "should_retry": final_state.get("should_retry", False),
        })

    except Exception as e:
        yield ("error", {"message": str(e)})


def _normalize_summary(s: dict) -> dict:
    """标准化 final_plan 字段，对齐前端 PlanResponse 期望的格式"""
    from datetime import date, timedelta
    s = dict(s)

    # === 1. 标准化天气字段（qweather 格式 → 前端标准格式） ===
    raw_wf = s.get("weather_forecast") or []
    if isinstance(raw_wf, list) and raw_wf:
        normalized = []
        for f in raw_wf:
            normalized.append({
                "date": f.get("date") or f.get("fxDate", ""),
                "weather": f.get("weather") or f.get("dayweather", ""),
                "temp_high": f.get("temp_high") or f.get("tempMax") or f.get("daytemp"),
                "temp_low": f.get("temp_low") or f.get("tempMin") or f.get("nighttemp"),
                "wind": f.get("wind") or (f.get("daywind", "") + (" " + f.get("daypower", "") + "级" if f.get("daypower") else "")),
                "humidity": f.get("humidity"),
                "precipitation": f.get("precipitation"),
                "aqi": f.get("aqi"),
                "advice": f.get("advice") or f.get("text", ""),
            })
        s["weather_forecast"] = normalized

    # === 1.5 修正天气日期年份（LLM 有时生成 2025 年） ===
    this_year = str(date.today().year)
    for f in (s.get("weather_forecast") or []):
        fd = f.get("date", "")
        if fd and fd.startswith("2025-") and this_year != "2025":
            f["date"] = this_year + fd[4:]

    if not raw_wf and s.get("days"):
        # 天气回退：生成默认预报
        days = int(s["days"])
        s["weather_forecast"] = [
            {
                "date": str(date.today() + timedelta(days=i)),
                "weather": "晴",
                "temp_high": "30",
                "temp_low": "22",
                "wind": "微风",
                "advice": "适宜出行",
            }
            for i in range(days)
        ]

    # === 2. 合并 meal_plan 到 daily_itinerary 的每一天 ===
    daily = s.get("daily_itinerary") or s.get("daily_plan") or []
    meal_plan = s.get("meal_plan") or []
    # 如果 meal_plan 为空但 food_details 有数据，从 food_details 构建
    if isinstance(meal_plan, list) and not meal_plan:
        fd = s.get("food_details") or []
        if fd and isinstance(daily, list):
            half = (len(fd) + 1) // 2
            meal_plan = [
                {"day": i + 1, "meals": [
                    {"meal": "午餐", "restaurant": fd[i].get("name", "推荐餐厅"), "avg_price": fd[i].get("avg_price", 0), "reason": "推荐"},
                ]} for i in range(min(len(fd), len(daily)))
            ]
            s["meal_plan"] = meal_plan
    if isinstance(meal_plan, list) and meal_plan:
        mp_by_day = {m.get("day"): m.get("meals", []) for m in meal_plan if m.get("day")}
        for day in daily:
            day_num = day.get("day")
            if day_num and not day.get("meals"):
                day["meals"] = mp_by_day.get(day_num, [])
            # 补 weather_summary（如果当天没有但 weather_forecast 有）
            if not day.get("weather_summary") and isinstance(raw_wf, list):
                idx = day_num - 1 if isinstance(day_num, int) else 0
                if 0 <= idx < len(raw_wf):
                    fc = raw_wf[idx]
                    day["weather_summary"] = fc.get("summary") or f"{fc.get('dayweather','')} {fc.get('daytemp','')}°C / {fc.get('nighttemp','')}°C"

    # === 3. 确保 daily_itinerary 存在 ===
    if daily and not s.get("daily_itinerary"):
        s["daily_itinerary"] = daily

    # === 4. big_traffic 统一为列表 ===
    bt = s.get("big_traffic")
    if isinstance(bt, dict):
        s["big_traffic"] = [bt]
    elif bt is None:
        s["big_traffic"] = []

    # === 5. 补 hotel_plan 的 selected_hotel（如果缺失） ===
    hp = s.get("hotel_plan") or {}
    if isinstance(hp, dict) and hp.get("recommendations") and not hp.get("selected_hotel"):
        recs = hp["recommendations"]
        selected_name = hp.get("selected")
        if selected_name:
            match = next((r for r in recs if r.get("name") == selected_name), None)
            if match:
                hp["selected_hotel"] = match
        if not hp.get("selected_hotel") and recs:
            hp["selected_hotel"] = recs[0]
            hp["selected"] = recs[0].get("name")

    return s


async def _llm_fallback(s: dict[str, Any]) -> None:
    """当天气/餐饮数据为空时，用 DeepSeek LLM 生成回退数据"""
    dest = s.get("destination", "")
    days = int(s.get("days", 0) or 0)
    origin = s.get("origin", "")
    if not dest or not days:
        return

    llm = DeepSeekLLM()
    need_weather = not s.get("weather_forecast")
    need_meals = not s.get("meal_plan") and not s.get("food_details")

    import logging
    logging.getLogger(__name__).info(f"[llm_fallback] dest={dest} days={days} need_weather={need_weather} need_meals={need_meals}")

    if not need_weather and not need_meals:
        return

    from datetime import date as dt_date
    today = dt_date.today().isoformat()
    prompt_parts = []
    if need_weather:
        prompt_parts.append(
            f"为{dest}从{today}开始的{days}天天气预报。"
            f"注意：今天的日期是{today}，返回的日期必须从{today}开始且年份是2026年。"
            f"JSON格式：{{'forecasts':[{{'date':'{today}','weather':'晴/多云等','temp_high':35,'temp_low':25,'wind':'南风3级','advice':'建议'}}]}}"
        )
    if need_meals:
        prompt_parts.append(f"为{dest}{days}天旅行推荐三餐，每日期/晚餐，JSON格式：{{'meal_plan':[{{'day':1,'meals':[{{'meal':'午餐','restaurant':'店名','avg_price':50,'reason':'理由'}},{{'meal':'晚餐','restaurant':'店名','avg_price':60,'reason':'理由'}}]}}]}}")

    prompt = f"目的地：{dest}，出发地：{origin}，天数：{days}。\n" + "\n".join(prompt_parts) + "\n只返回JSON，不要其他文字。"
    try:
        resp = await asyncio.wait_for(llm.chat([{"role": "user", "content": prompt}]), timeout=30.0)
        data = _extract_json(resp)
        if need_weather and "forecasts" in data:
            s["weather_forecast"] = data["forecasts"]
        if need_meals and "meal_plan" in data:
            s["meal_plan"] = data["meal_plan"]
    except Exception:
        pass


def _extract_json(text: str) -> dict:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        text = m.group(1).strip()
    m = re.search(r"\{[\s\S]*\}", text)
    return json.loads(m.group(0)) if m else {}
