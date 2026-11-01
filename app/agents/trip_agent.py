"""
TripAgent — 行程执行状态管理

职责:
- 从方案创建行程执行实例
- 状态机管理（active/paused/completed/abandoned）
- 签到处理 + 进度计算
- 每日提醒生成
- 预算追踪
"""

from datetime import datetime
from typing import Any

from app.agents.base import BaseAgent
from app.services.llm.base import BaseLLM


class TripAgent(BaseAgent):
    name = "trip"
    description = "行程执行状态管理 — 签到/进度/提醒/预算追踪"

    def __init__(self, llm: BaseLLM):
        super().__init__(llm)

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """兼容 BaseAgent 接口，根据 action 分发"""
        action = input_data.get("action", "get_progress")
        if action == "start":
            return await self.start_trip(input_data)
        elif action == "checkin":
            return await self.process_checkin(input_data)
        elif action == "reminder":
            return await self.generate_reminder(input_data)
        elif action == "progress":
            return await self._calculate_progress(input_data)
        return {"error": f"Unknown action: {action}"}

    # ========== 开始行程 ==========

    async def start_trip(self, plan: dict) -> dict:
        """
        从 final_plan 提取行程元信息:
        - 总打卡目标数（景点 + 餐厅）
        - 按天分布
        - 预算信息
        """
        itinerary = plan.get("daily_itinerary", plan.get("daily_plan", []))
        total_pois = 0
        days_outline = []

        for day in itinerary:
            d = day.get("day", len(days_outline) + 1)
            attractions = day.get("attractions", [])
            meals = day.get("meals", [])
            all_stops = []

            for a in attractions:
                all_stops.append({"type": "attraction", "name": a.get("name", ""),
                                  "planned_time": a.get("planned_time", "09:00"),
                                  "duration_h": a.get("duration_hours", 2),
                                  "expected_cost": a.get("price", 0)})
            for m in meals:
                all_stops.append({"type": "restaurant", "name": m.get("restaurant", ""),
                                  "planned_time": _meal_planned_time(m.get("meal", "")),
                                  "duration_h": 1,
                                  "expected_cost": m.get("avg_price", 0)})

            total_pois += len(all_stops)
            days_outline.append({"day": d, "stops": all_stops})

        budget = plan.get("budget", {})
        return {
            "total_pois": total_pois,
            "total_days": len(days_outline),
            "days_outline": days_outline,
            "budget_total": budget.get("total", plan.get("total_budget", 0)),
            "budget_allocation": budget.get("allocation", {}),
        }

    # ========== 签到处理 ==========

    async def process_checkin(self, data: dict) -> dict:
        """
        处理签到事件:
        - 计算时间偏差
        - 更新进度
        - 检测是否需要触发调整
        """
        # 兼容 planned_at 和 planned_time 两种 key
        planned_time = data.get("planned_time") or data.get("planned_at", "")
        actual_time = data.get("actual_at") or datetime.utcnow()

        # 计算时间偏差
        time_delta_min = 0
        if isinstance(planned_time, str) and planned_time:
            try:
                planned_h, planned_m = map(int, planned_time.split(":"))
                if isinstance(actual_time, datetime):
                    actual_h, actual_m = actual_time.hour, actual_time.minute
                elif isinstance(actual_time, str) and "T" in actual_time:
                    tpart = actual_time.split("T")[1][:5]
                    actual_h, actual_m = map(int, tpart.split(":"))
                else:
                    actual_h, actual_m = 0, 0
                time_delta_min = (actual_h * 60 + actual_m) - (planned_h * 60 + planned_m)
            except (ValueError, AttributeError):
                pass

        # 计算花费偏差
        planned_cost = float(data.get("planned_cost", 0) or 0)
        actual_cost = float(data.get("actual_cost", 0) or 0)
        cost_delta = actual_cost - planned_cost

        # 判断是否触发调整
        trigger_adjustment = False
        trigger_reason = ""
        if time_delta_min > 30:
            trigger_adjustment = True
            trigger_reason = f"late_{time_delta_min}min"
        elif time_delta_min < -30:
            trigger_adjustment = True
            trigger_reason = f"early_{abs(time_delta_min)}min"
        if cost_delta > planned_cost * 0.5 and planned_cost > 0:
            trigger_adjustment = True
            trigger_reason += f" over_budget_{cost_delta:.0f}"

        return {
            "time_delta_min": time_delta_min,
            "on_time": abs(time_delta_min) <= 15,
            "cost_delta": round(cost_delta, 2),
            "on_budget": cost_delta <= 0,
            "trigger_adjustment": trigger_adjustment,
            "trigger_reason": trigger_reason,
            "updated_progress": data.get("current_progress", 0),
        }

    # ========== 每日提醒 ==========

    async def generate_reminder(self, data: dict) -> dict:
        """生成不依赖 LLM 的准确次日提醒。"""
        return build_trip_reminder(data)

    # ========== 进度计算 ==========

    async def _calculate_progress(self, data: dict) -> dict:
        total = max(data.get("total_pois", 0), 1)
        checked = data.get("checked_in", 0)
        current_day = data.get("current_day", 1)
        total_days = max(data.get("total_days", 1), 1)

        poi_pct = round(checked / total * 100, 1)
        day_pct = round(current_day / total_days * 100, 1)
        overall_pct = round((poi_pct + day_pct) / 2, 1)

        ahead = checked > (total / total_days * current_day)

        return {
            "poi_progress_pct": poi_pct,
            "day_progress_pct": day_pct,
            "overall_progress_pct": overall_pct,
            "checked_in": checked,
            "total_pois": total,
            "current_day": current_day,
            "total_days": total_days,
            "ahead_of_schedule": ahead,
            "status": "ahead" if ahead else ("on_track" if poi_pct >= day_pct - 10 else "behind"),
        }


# ================================================================
#  Helpers
# ================================================================

def _meal_planned_time(meal: str) -> str:
    mapping = {"早餐": "08:00", "午餐": "12:00", "晚餐": "18:00"}
    return mapping.get(meal, "12:00")


def build_trip_reminder(data: dict) -> dict:
    current_day = max(int(data.get("current_day") or 1), 1)
    total_days = max(int(data.get("total_days") or 0), 0)
    tomorrow_day = int(data.get("tomorrow_day") or current_day + 1)
    weather = data.get("weather") if isinstance(data.get("weather"), dict) else {}
    if data.get("is_last_day") or (total_days and tomorrow_day > total_days):
        return {
            "day": current_day,
            "is_last_day": True,
            "reminder_text": "",
            "first_stop": "",
            "first_stop_time": "",
            "weather_advice": "",
            "packing_hint": "",
            "weather": weather,
        }

    day_outline = data.get("day_outline") if isinstance(data.get("day_outline"), dict) else {}
    stops = day_outline.get("stops") if isinstance(day_outline.get("stops"), list) else []
    first_stop = stops[0] if stops else {}
    attractions = [stop.get("name", "") for stop in stops if stop.get("type") == "attraction"]
    restaurants = [stop.get("name", "") for stop in stops if stop.get("type") == "restaurant"]

    itinerary_parts = []
    if attractions:
        itinerary_parts.append(f"景点安排为{'、'.join(attractions[:4])}")
    if restaurants:
        itinerary_parts.append(f"用餐安排为{'、'.join(restaurants[:2])}")
    itinerary_text = "；".join(itinerary_parts) or "请按原行程从容安排"

    condition = str(weather.get("condition") or "").strip()
    temp_high = weather.get("temp_high")
    temp_low = weather.get("temp_low")
    weather_parts = []
    if condition:
        weather_parts.append(condition)
    if temp_high is not None and temp_low is not None:
        weather_parts.append(f"{temp_low:g}~{temp_high:g}°C")
    elif temp_high is not None:
        weather_parts.append(f"最高{temp_high:g}°C")
    elif temp_low is not None:
        weather_parts.append(f"最低{temp_low:g}°C")
    weather_text = f"预计天气{'，'.join(weather_parts)}。" if weather_parts else ""
    advice = str(weather.get("advice") or "").strip()
    advice_text = f"{advice.rstrip('。')}。" if advice else ""

    first_stop_name = str(first_stop.get("name") or "")
    first_stop_time = str(first_stop.get("planned_time") or "")
    departure_text = (
        f"首站{first_stop_name}，建议{first_stop_time or '按计划时间'}出发。"
        if first_stop_name else ""
    )
    reminder_text = (
        f"明天是第{tomorrow_day}天：{itinerary_text}。"
        f"{weather_text}{advice_text}{departure_text}"
    )

    return {
        "day": tomorrow_day,
        "is_last_day": False,
        "reminder_text": reminder_text,
        "first_stop": first_stop_name,
        "first_stop_time": first_stop_time,
        "weather_advice": weather.get("advice", ""),
        "packing_hint": _packing_hint(weather),
        "weather": weather,
    }


def _packing_hint(weather: dict) -> str:
    temp_h = weather.get("temp_high")
    condition = str(weather.get("condition") or "")
    rain = any(word in condition for word in ["雨", "雪", "storm"])
    hints = ["充电宝", "水杯"]
    if temp_h is not None and temp_h > 30:
        hints.extend(["防晒霜", "遮阳帽", "墨镜"])
    elif temp_h is not None and temp_h < 15:
        hints.extend(["外套", "围巾"])
    if rain:
        hints.append("雨伞")
    return "、".join(hints)
