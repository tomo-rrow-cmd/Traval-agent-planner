"""旅行方案 Repository"""

from datetime import date, datetime
from typing import Any, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.plan import Plan
from app.db.repositories.base import BaseRepository


class PlanRepository(BaseRepository[Plan]):
    """旅行方案数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(Plan, db)

    async def create_for_user(
        self,
        user_id: str,
        destination: str,
        start_date: date,
        end_date: date,
        budget: float,
        travelers: int = 1,
        preferences: list[str] | None = None,
        status: str = "generating",
        departure: str | None = None,
        crowd_type: str | None = None,
        travel_style: str | None = None,
        plan_id: str | None = None,
    ) -> Plan:
        """为指定用户创建旅行方案"""
        plan = Plan(
            id=plan_id,
            user_id=user_id,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            travelers=travelers,
            preferences=preferences or [],
            status=status,
            itinerary=[],
            departure=departure,
            crowd_type=crowd_type,
            travel_style=travel_style,
        )
        return await self.create(plan)

    async def mark_as_saved(self, plan_id: str, user_id: str) -> Plan | None:
        """将方案标记为用户主动保存"""
        plan = await self.get_by_id_for_user(plan_id, user_id)
        if plan is None:
            return None
        plan.saved_at = datetime.utcnow()
        await self.db.flush()
        return plan

    async def update_full_data(self, plan_id: str, full_data: dict[str, Any]) -> Plan | None:
        """将 final_plan 完整数据写入 Plan 记录的各字段"""
        plan = await self.get_by_id(plan_id)
        if plan is None:
            return None

        plan.full_data = full_data

        # 顶级标量字段
        if full_data.get("departure"):
            plan.departure = full_data["departure"]
        if full_data.get("origin"):
            plan.departure = full_data["origin"]
        if full_data.get("crowd_type"):
            plan.crowd_type = full_data["crowd_type"]
        if full_data.get("travel_style"):
            plan.travel_style = full_data["travel_style"]
        if full_data.get("total_cost"):
            plan.total_cost = full_data["total_cost"]
        elif full_data.get("estimated_cost"):
            plan.total_cost = full_data["estimated_cost"]
        if full_data.get("days"):
            plan.end_date = plan.start_date  # fallback
            from datetime import timedelta
            plan.end_date = plan.start_date + timedelta(days=int(full_data["days"]) - 1)

        # 嵌套 JSON 字段
        plan.overview = full_data.get("overview", {})
        plan.traffic_summary = _build_traffic_summary(full_data)
        plan.food_summary = _build_food_summary(full_data)
        plan.budget_detail = _build_budget_detail(full_data)
        plan.souvenir_recommendations = full_data.get("souvenirs", full_data.get("souvenir_recommendations", []))
        plan.weather_forecast = full_data.get("weather_forecast", [])
        plan.packing_list = full_data.get("packing_list", [])
        plan.tips = full_data.get("tips", [])
        plan.avoid_list = full_data.get("avoid_list", [])
        plan.hotel_plan = full_data.get("hotel_plan", {})
        plan.meal_plan = full_data.get("meal_plan", [])
        plan.attraction_details = full_data.get("attraction_details", [])
        plan.food_details = full_data.get("food_details", [])

        # big_traffic: 统一为数组
        raw_bt = full_data.get("big_traffic", [])
        if isinstance(raw_bt, dict):
            plan.big_traffic = [raw_bt]
        else:
            plan.big_traffic = raw_bt

        # itinerary: 从 daily_itinerary 或 daily_plan 提取基本行程
        daily = full_data.get("daily_itinerary", full_data.get("daily_plan", []))
        if daily:
            plan.itinerary = daily

        await self.db.flush()
        return plan

    async def get_by_id_for_user(self, plan_id: str, user_id: str) -> Plan | None:
        """按方案 ID 和用户 ID 查询方案"""
        result = await self.db.execute(
            select(Plan).where(Plan.id == plan_id, Plan.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def upsert_plan_from_summary(
        self,
        user_id: str,
        plan_id: str | None,
        summary: dict[str, Any],
        destination: str,
        start_date: date,
        end_date: date,
        budget: float,
        travelers: int = 1,
    ) -> Plan:
        """根据 ConversationPlanRun.summary 创建或更新 Plan 记录"""
        existing = None
        if plan_id:
            existing = await self.get_by_id(plan_id)
        if existing is not None:
            plan = await self.update_full_data(existing.id, summary)
            return plan

        plan = await self.create_for_user(
            user_id=user_id,
            destination=destination,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            travelers=travelers,
            preferences=summary.get("preferences", []),
            status="completed",
            departure=summary.get("origin") or summary.get("departure"),
            crowd_type=summary.get("crowd_type"),
            travel_style=summary.get("travel_style"),
            plan_id=plan_id,
        )
        await self.update_full_data(plan.id, summary)
        return plan

    async def list_by_user(
        self,
        user_id: str,
        offset: int = 0,
        limit: int = 20,
        status: str | None = None,
        saved_only: bool = False,
    ) -> Sequence[Plan]:
        """分页查询用户方案"""
        query = select(Plan).where(Plan.user_id == user_id)
        if status:
            query = query.where(Plan.status == status)
        if saved_only:
            query = query.where(Plan.saved_at.isnot(None))
        query = query.order_by(Plan.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: str, status: str | None = None, saved_only: bool = False) -> int:
        """统计用户方案数量"""
        from sqlalchemy import func
        query = select(func.count(Plan.id)).where(Plan.user_id == user_id)
        if status:
            query = query.where(Plan.status == status)
        if saved_only:
            query = query.where(Plan.saved_at.isnot(None))
        result = await self.db.execute(query)
        return result.scalar() or 0


def _build_traffic_summary(full_data: dict) -> dict:
    """从 final_plan 构建 traffic_summary"""
    traffic = full_data.get("traffic", {})
    big_traffic = full_data.get("big_traffic", {})
    if isinstance(big_traffic, list):
        big_traffic = big_traffic[0] if big_traffic else {}

    city_to_city = []
    raw_bt = full_data.get("big_traffic", [])
    if isinstance(raw_bt, list):
        for entry in raw_bt:
            for t in entry.get("trains", [])[:3]:
                price_str = t.get("prices", {})
                first_price = next(iter(price_str.values()), None) if isinstance(price_str, dict) else None
                city_to_city.append({
                    "mode": "火车",
                    "from": t.get("fromStationName", ""),
                    "to": t.get("toStationName", ""),
                    "price": first_price,
                    "duration": t.get("duration", ""),
                    "recommendation": f"{t.get('trainCode', '')} {t.get('departureTime', '')}-{t.get('arrivalTime', '')}",
                })
            for f in entry.get("flights", [])[:2]:
                city_to_city.append({
                    "mode": "飞机",
                    "from": full_data.get("origin", ""),
                    "to": full_data.get("destination", ""),
                    "price": None,
                    "duration": "",
                    "recommendation": f"{f.get('flight', '')} {f.get('dep', '')}-{f.get('arr', '')}",
                })

    return {
        "city_to_city": city_to_city,
        "city_internal": traffic.get("summary", ""),
        "total_traffic_cost": traffic.get("total_traffic_cost", 0),
    }


def _build_food_summary(full_data: dict) -> dict:
    """从 final_plan 构建 food_summary"""
    meal_plan = full_data.get("meal_plan", [])
    total = 0
    seen = set()
    restaurants = []
    for day in meal_plan:
        for m in day.get("meals", []):
            name = m.get("restaurant", "")
            if name and name not in seen:
                seen.add(name)
                restaurants.append({
                    "name": name,
                    "cuisine": m.get("cuisine", ""),
                    "avg_price": m.get("avg_price", 0),
                    "rating": m.get("rating", 0),
                    "recommended_dishes": [],
                })
            total += m.get("avg_price", 0)

    return {
        "recommended_restaurants": restaurants,
        "total_food_budget": total,
    }


def _build_budget_detail(full_data: dict) -> dict:
    """从 final_plan 构建 budget_detail"""
    budget = full_data.get("budget", {})
    details = budget.get("details", [])
    total_budget = budget.get("total_budget", full_data.get("total_budget", 0))
    actual_total = budget.get("actual_total", full_data.get("estimated_cost", 0))

    cat_map = {
        "transport": ["交通", "transport", "traffic"],
        "accommodation": ["住宿", "accommodation", "hotel"],
        "food": ["餐饮", "food", "meal"],
        "attractions": ["门票", "attractions", "ticket"],
        "souvenirs": ["购物", "souvenirs", "shopping"],
        "contingency": ["备用", "contingency", "other"],
    }

    breakdown = {}
    for key, names in cat_map.items():
        spent = 0
        items = []
        for d in details:
            if d.get("category") in names:
                spent = d.get("spent", 0)
                break
        breakdown[key] = {
            "amount": spent,
            "percent": round(spent / total_budget * 100, 1) if total_budget > 0 else 0,
            "items": items,
        }

    return {
        "total": float(total_budget),
        "actual_total": float(actual_total),
        "remaining": float(budget.get("remaining", max(total_budget - actual_total, 0))),
        "breakdown": breakdown,
        "warnings": budget.get("warnings", []),
        "suggestions": budget.get("suggestions", []),
        "per_person_per_day": budget.get("per_person_per_day", 0),
    }
