"""
BudgetAgent — 动态分配 + 修正建议 + 最终方案

分配基于: 城市等级、偏好、天数、旺季系数
"""

from typing import Any

from app.agents.base import BaseAgent

CITY_TIER = {
    "北京": 1.4, "上海": 1.4, "深圳": 1.3, "广州": 1.2, "杭州": 1.2,
    "三亚": 1.5, "厦门": 1.2, "青岛": 1.1, "成都": 1.0, "武汉": 0.9,
    "西安": 0.9, "重庆": 0.9, "南京": 1.0, "大连": 1.0, "昆明": 0.9,
    "长沙": 0.9, "郑州": 0.8, "济南": 0.8, "天津": 0.9, "苏州": 1.1,
}
BASE = {"住宿": 0.35, "交通": 0.20, "餐饮": 0.20, "门票": 0.15, "购物": 0.10}


class BudgetAgent(BaseAgent):
    name = "budget"
    description = "动态分配 + 修正建议 + 循环重规划"

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        total = float(input_data.get("total_budget", 0))
        reserve = float(input_data.get("reserve_budget", 0) or 0)
        planning = float(
            input_data.get("planning_budget")
            or max(total - reserve, 0)
            or total
        )
        days = int(input_data.get("days", 1))
        travelers = int(input_data.get("travelers", 1))
        destination = input_data.get("destination", "")
        origin = input_data.get("origin", "")
        start_date = str(input_data.get("start_date") or "")
        end_date = str(input_data.get("end_date") or "")
        preferences = input_data.get("preferences", [])
        cuisine_preferences = input_data.get("cuisine_preferences", [])
        if not isinstance(preferences, list):
            preferences = [str(preferences)] if str(preferences).strip() else []
        preferences_provided = bool(input_data.get("preferences_provided", True))
        budget_no_limit = bool(input_data.get("budget_no_limit", False))
        pace = input_data.get("pace", "适中")
        preferred_transport = input_data.get("preferred_transport", "地铁")
        preferred_transport_provided = bool(
            input_data.get("preferred_transport_provided", False)
        )
        hotel_star = int(input_data.get("hotel_star") or 3)
        hotel_budget = float(input_data.get("hotel_budget") or 500)
        meal_budget = float(input_data.get("meal_budget") or 100)
        cuisine_preferences = input_data.get("cuisine_preferences", [])
        if not isinstance(cuisine_preferences, list):
            cuisine_preferences = [
                str(cuisine_preferences)
            ] if str(cuisine_preferences).strip() else []
        preferred_transport = str(input_data.get("preferred_transport") or "地铁")
        expenses = input_data.get("expenses", {})
        retry = input_data.get("retry_count", 0)

        alloc = _dynamic(planning, destination, preferences, days)
        actual = {
            "住宿": expenses.get("hotels", 0),
            "交通": expenses.get("traffic", 0),
            "餐饮": expenses.get("meals", 0),
            "门票": expenses.get("attractions", 0),
            "购物": expenses.get("shopping", 0),
        }
        actual_total = sum(actual.values())
        over_pct = (actual_total - planning) / planning * 100 if planning > 0 else 0

        details, warnings = [], []
        for cat in alloc:
            budgeted = alloc[cat]
            spent = actual.get(cat, 0)
            details.append({
                "category": cat,
                "budget": round(budgeted, 2),
                "spent": round(spent, 2),
                "remaining": round(budgeted - spent, 2),
                "status": "over" if spent > budgeted else "ok",
            })
            if spent > budgeted * 1.2:
                warnings.append(f"{cat}超预算 ¥{spent - budgeted:.0f}")
        if planning > 0 and actual_total > planning:
            warnings.append(f"总费用超规划预算 ¥{actual_total - planning:.0f} ({over_pct:.0f}%)")
        elif planning > 0 and actual_total > planning * 0.85:
            warnings.append(f"已用 {actual_total / planning * 100:.0f}%，接近上限")

        suggestions = _suggest(details, over_pct, retry)
        should_retry = 0 < over_pct <= 30 and retry < 2
        adjusted = _adj(details, retry) if should_retry else {}
        per_person_day = actual_total / travelers / days if travelers > 0 and days > 0 else 0

        daily_itinerary = input_data.get("daily_itinerary", [])
        meal_plan = input_data.get("meal_plan", [])
        hotel_plan = input_data.get("hotel_plan", {})
        traffic_data = input_data.get("traffic", {})
        big_traffic = traffic_data.get("big_traffic", input_data.get("big_traffic", {}))

        budget_config = {
            "total_budget": total,
            "reserve_budget": reserve,
            "planning_budget": planning,
        }
        budget_plan = {
            "total": total,
            "total_budget": total,
            "reserve_budget": reserve,
            "planning_budget": planning,
            "actual_total": round(actual_total, 2),
            "remaining": round(planning - actual_total, 2),
            "total_remaining": round(total - actual_total, 2),
            "allocation": alloc,
            "details": details,
            "warnings": warnings,
            "suggestions": suggestions,
            "over_pct": round(over_pct, 1),
            "retry_count": retry,
            "per_person_per_day": round(per_person_day, 2),
        }

        final = {
            "trip_name": f"{destination}{days}日之旅",
            "summary": f"{origin}出发，{destination}{days}日游",
            "destination": destination,
            "origin": origin,
            "start_date": start_date,
            "end_date": end_date,
            "days": days,
            "cuisine_preferences": cuisine_preferences,
            "preferred_transport": preferred_transport,
            "preferred_transport_provided": preferred_transport_provided,
            "trip_config": {
                "destination": destination,
                "origin": origin,
                "start_date": start_date,
                "end_date": end_date,
                "days": days,
                "total_budget": total,
                "reserve_budget": reserve,
                "planning_budget": planning,
                "budget_no_limit": budget_no_limit,
                "preferences": preferences,
                "cuisine_preferences": cuisine_preferences,
                "preferences_provided": preferences_provided,
                "pace": pace,
                "preferred_transport": preferred_transport,
                "preferred_transport_provided": preferred_transport_provided,
                "hotel_star": hotel_star,
                "hotel_budget": hotel_budget,
                "meal_budget": meal_budget,
                "travelers": travelers,
                "budget": budget_config,
            },
            "daily_itinerary": daily_itinerary,
            "daily_plan": daily_itinerary,
            "meal_plan": meal_plan,
            "hotel_plan": hotel_plan,
            "meituan_hotels": input_data.get("meituan_hotels", []),
            "attraction_details": input_data.get("attraction_details", []),
            "food_details": input_data.get("food_details", []),
            "traffic": {
                "daily_traffic": traffic_data.get("daily_traffic", []),
                "total_cost": traffic_data.get("total_traffic_cost", 0),
                "time_warnings": traffic_data.get("time_warnings", []),
                "summary": traffic_data.get("summary", ""),
                "hotel_match": traffic_data.get("hotel_match", {}),
            },
            "big_traffic": {
                "trains": big_traffic.get("trains", []) if isinstance(big_traffic, dict) else big_traffic,
                "flights": big_traffic.get("flights", []) if isinstance(big_traffic, dict) else [],
                "recommend_mode": big_traffic.get("recommend_mode", "") if isinstance(big_traffic, dict) else "",
                "city_distance_km": big_traffic.get("city_distance_km", 0) if isinstance(big_traffic, dict) else 0,
                "origin_hub": big_traffic.get("origin_hub", None) if isinstance(big_traffic, dict) else None,
                "arrival_hub": big_traffic.get("arrival_hub", None) if isinstance(big_traffic, dict) else None,
                "departure_hub": big_traffic.get("departure_hub", None) if isinstance(big_traffic, dict) else None,
                "hub_to_hotel": big_traffic.get("hub_to_hotel", None) if isinstance(big_traffic, dict) else None,
            },
            "budget": budget_plan,
        }

        return {
            "final_plan": final,
            "budget_plan": budget_plan,
            "total_budget": total,
            "reserve_budget": reserve,
            "planning_budget": planning,
            "budget_allocation": alloc,
            "actual_details": details,
            "actual_total": round(actual_total, 2),
            "remaining": round(planning - actual_total, 2),
            "total_remaining": round(total - actual_total, 2),
            "per_person_per_day": round(per_person_day, 2),
            "warnings": warnings,
            "suggestions": suggestions,
            "over_pct": round(over_pct, 1),
            "should_retry": should_retry,
            "adjusted_params": adjusted,
            "retry_count": retry + 1,
        }


def _dynamic(total: float, city: str, prefs: list, days: int) -> dict:
    a = dict(BASE)
    tier = CITY_TIER.get(city, 1.0)
    a["住宿"] = round(a["住宿"] * max(0.7, min(1.6, tier)), 2)
    pt = " ".join(prefs).lower() if prefs else ""
    if any(w in pt for w in ["美食", "吃", "火锅"]):
        a["餐饮"] = round(a["餐饮"] + 0.08, 2); a["住宿"] = round(a["住宿"] - 0.08, 2)
    if any(w in pt for w in ["穷游", "省钱"]):
        a["住宿"] = round(a["住宿"] - 0.12, 2); a["门票"] = round(a["门票"] + 0.07, 2)
    if days <= 2:
        a["交通"] = round(a["交通"] + 0.05, 2); a["住宿"] = round(a["住宿"] - 0.05, 2)
    s = sum(a.values())
    return {k: round(total * v / s, 2) for k, v in a.items()}


def _suggest(details: list, over_pct: float, retry: int) -> list:
    s = []
    for d in details:
        if d["status"] != "over": continue
        ov = abs(d["remaining"])
        if d["category"] == "住宿":
            s.append({"action": "降酒店星级", "save": round(ov * 0.6)})
            s.append({"action": "降每晚预算", "save": round(ov * 0.4)})
        elif d["category"] == "餐饮":
            s.append({"action": "降人均餐标 Y30", "save": round(ov * 0.5)})
        elif d["category"] == "交通":
            s.append({"action": "地铁替代打车", "save": round(ov * 0.7)})
        elif d["category"] == "门票":
            s.append({"action": "换免费景点", "save": round(ov)})
    if over_pct > 30 and retry == 0:
        s.insert(0, {"action": "建议提高总预算", "save": 0})
    return s


def _adj(details: list, retry: int) -> dict:
    a = {}
    for d in details:
        if d["status"] != "over": continue
        if d["category"] == "住宿" and retry == 0:
            a["hotel_budget"] = max(200, int(d["spent"] * 0.7)); a["hotel_star"] = 2
        elif d["category"] == "餐饮":
            a["meal_budget"] = max(50, int(d["spent"] * 0.7))
    return a
