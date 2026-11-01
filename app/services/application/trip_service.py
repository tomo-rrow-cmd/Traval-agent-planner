"""行程执行业务服务 — TripService"""

import re
from datetime import datetime, date, timedelta, timezone
from typing import Any

from app.db.models.plan import Plan
from app.db.models.trip import TripState, Checkin, ExpenseRecord, Adjustment
from app.db.models.user import User
from app.db.repositories.plan_repo import PlanRepository
from app.db.repositories.trip_repo import (
    TripRepository, CheckinRepository, ExpenseRepository, AdjustmentRepository,
)
from app.schemas.common import PaginatedData


class TripService:
    """行程执行核心业务逻辑"""

    def __init__(self, trip_repo: TripRepository, checkin_repo: CheckinRepository,
                 expense_repo: ExpenseRepository, adj_repo: AdjustmentRepository,
                 plan_repo: PlanRepository | None = None):
        self.trip_repo = trip_repo
        self.checkin_repo = checkin_repo
        self.expense_repo = expense_repo
        self.adj_repo = adj_repo
        self.plan_repo = plan_repo

    # ---- Trip CRUD ----

    async def start_trip(self, user_id: str, plan_id: str, budget_total: float = 0,
                         plan_data: dict | None = None) -> dict:
        """从方案创建行程执行实例，自动统计总打卡目标数"""
        total_pois = 0
        plan = None
        # 尝试从数据库查找方案
        if self.plan_repo:
            plan = await self.plan_repo.get_by_id(plan_id)

        if plan:
            # 方案在 DB 中存在 → 从 itinerary 统计 POI
            if plan.itinerary:
                total_pois, budget_total = _count_pois_from_itinerary(plan.itinerary, budget_total)
            if not budget_total and isinstance(plan.budget, (int, float)):
                budget_total = float(plan.budget)
        elif plan_data:
            # 方案不在 DB 但前端传了 plan_data → 自动创建方案 + 行程
            plan = await self._create_plan_from_data(user_id, plan_id, plan_data)
            total_pois, budget_total = _count_pois_from_plan_data(plan_data, budget_total)
        else:
            raise ValueError(f"方案不存在: {plan_id}")

        trip = await self.trip_repo.create_for_plan(
            user_id, plan_id, budget_total=budget_total, total_pois=total_pois,
        )
        return self._trip_to_dict(trip)

    async def get_trip(self, trip_id: str, user_id: str) -> dict | None:
        trip = await self.trip_repo.get_by_id_for_user(trip_id, user_id)
        return self._trip_to_dict(trip) if trip else None

    async def list_trips(self, user_id: str, status: str | None = None,
                         page: int = 1, page_size: int = 20) -> PaginatedData:
        offset = (page - 1) * page_size
        trips = await self.trip_repo.list_by_user(user_id, status, offset, page_size)
        total = await self.trip_repo.count_by_user(user_id, status)
        return PaginatedData.create(
            [self._trip_to_dict(t) for t in trips],
            total=total, page=page, page_size=page_size,
        )

    async def update_status(self, trip_id: str, user_id: str, new_status: str) -> dict:
        trip = await self.trip_repo.get_by_id_for_user(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found")

        valid_transitions = {
            "active": ["paused", "completed", "abandoned"],
            "paused": ["active", "abandoned"],
        }
        current = trip.status
        if current in valid_transitions and new_status in valid_transitions[current]:
            trip.status = new_status
            now = datetime.utcnow()
            if new_status == "paused":
                trip.paused_at = now
            elif new_status == "completed":
                trip.completed_at = now
            elif new_status == "active" and current == "paused":
                trip.paused_at = None
            await self.trip_repo.update(trip)

        return self._trip_to_dict(trip)

    async def get_progress(self, trip_id: str, user_id: str) -> dict:
        trip = await self.trip_repo.get_by_id_for_user(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found")

        checkin_count = trip.checked_in or 0
        total_pois = trip.total_pois or 1
        progress_pct = round(checkin_count / max(total_pois, 1) * 100, 1)

        # 花费汇总
        total_spent = await self.expense_repo.sum_by_trip(trip_id)

        return {
            "trip_id": trip.id,
            "status": trip.status,
            "current_day": trip.current_day,
            "progress_pct": progress_pct,
            "checked_in": checkin_count,
            "total_pois": total_pois,
            "budget_total": trip.budget_total,
            "budget_spent": round(total_spent, 2),
            "budget_remain": round((trip.budget_total or 0) - total_spent, 2),
            "time_delta_total_min": 0,
            "last_location": {"lat": trip.last_lat, "lng": trip.last_lng} if trip.last_lat else None,
        }

    # ---- Day Advancement ----

    async def advance_day(self, trip_id: str, user_id: str) -> dict:
        trip = await self.trip_repo.get_by_id_for_user(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found")
        if trip.status != "active":
            raise ValueError(f"当前行程状态为 '{trip.status}'，无法推进天数")
        if self.plan_repo:
            plan = await self.plan_repo.get_by_id(trip.plan_id)
            total_days = _get_plan_total_days(plan)
            if total_days and (trip.current_day or 1) >= total_days:
                raise ValueError("已是行程最后一天，请直接完成旅行")
        trip.current_day = (trip.current_day or 1) + 1
        await self.trip_repo.update(trip)
        return self._trip_to_dict(trip)

    async def get_reminder_context(self, trip_id: str, user_id: str) -> dict:
        """读取真实方案，构造下一日提醒上下文。"""
        trip = await self.trip_repo.get_by_id_for_user(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found")

        plan = await self.plan_repo.get_by_id(trip.plan_id) if self.plan_repo else None
        daily_itinerary = _get_plan_daily_itinerary(plan)
        total_days = _get_plan_total_days(plan)
        current_day = max(int(trip.current_day or 1), 1)
        is_last_day = bool(total_days and current_day >= total_days)
        context = {
            "current_day": current_day,
            "total_days": total_days,
            "is_last_day": is_last_day,
            "destination": getattr(plan, "destination", "") if plan else "",
            "day_outline": {"stops": []},
            "weather": {},
        }
        if is_last_day:
            return context

        tomorrow_day = current_day + 1
        tomorrow_plan = next(
            (
                day for index, day in enumerate(daily_itinerary, start=1)
                if int(day.get("day") or index) == tomorrow_day
            ),
            {},
        )
        context.update({
            "tomorrow_day": tomorrow_day,
            "day_outline": _build_reminder_day_outline(tomorrow_plan),
            "weather": _get_plan_day_weather(plan, tomorrow_day, tomorrow_plan),
        })
        return context

    async def get_travelogue_context(self, trip_id: str, user_id: str) -> dict:
        """聚合整趟旅行游记所需的方案与实际执行数据。"""
        trip = await self.trip_repo.get_by_id_for_user(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found")

        plan = await self.plan_repo.get_by_id(trip.plan_id) if self.plan_repo else None
        daily_itinerary = _get_plan_daily_itinerary(plan)
        checkin_models = await self.checkin_repo.list_by_trip(
            trip_id, day=None, offset=0, limit=500,
        )
        expense_models = await self.expense_repo.list_by_trip(trip_id, category=None)
        checkins = [self._checkin_to_dict(checkin) for checkin in checkin_models]
        expenses = [self._expense_to_dict(expense) for expense in expense_models]
        expense_total = round(sum(float(item.get("amount") or 0) for item in expenses), 2)
        actual_total = expense_total if expense_total > 0 else round(float(trip.budget_spent or 0), 2)

        full_data = getattr(plan, "full_data", None)
        full_data = full_data if isinstance(full_data, dict) else {}
        destination = str(
            full_data.get("destination")
            or getattr(plan, "destination", "")
            or ""
        )
        start_date = getattr(plan, "start_date", None)
        end_date = getattr(plan, "end_date", None)
        total_days = _get_plan_total_days(plan) or max(int(trip.current_day or 1), 1)
        planned_total_pois, _ = _count_pois_from_itinerary(daily_itinerary, 0)

        return {
            "trip_id": trip.id,
            "plan_id": trip.plan_id,
            "destination": destination,
            "start_date": start_date.isoformat() if isinstance(start_date, date) else str(start_date or ""),
            "end_date": end_date.isoformat() if isinstance(end_date, date) else str(end_date or ""),
            "total_days": total_days,
            "planned_total_pois": planned_total_pois,
            "actual_total_cost": actual_total,
            "daily_itinerary": daily_itinerary,
            "checkins": checkins,
            "expenses": expenses,
            "trip_status": trip.status,
        }

    # ---- Checkin ----

    async def checkin(self, trip_id: str, user_id: str,
                      poi_type: str, poi_name: str, **kwargs) -> dict:
        trip = await self.trip_repo.get_by_id_for_user(trip_id, user_id)
        if not trip:
            raise ValueError("Trip not found")

        if trip.status != "active":
            raise ValueError(f"当前行程状态为 '{trip.status}'，无法签到")

        existing = await self.checkin_repo.get_by_trip_and_poi(trip_id, poi_name)
        if existing:
            raise ValueError(f"'{poi_name}' 已签到过了")

        # B3: 将字符串 actual_at 转为 datetime（来自 API JSON → pydantic str）
        raw_actual = kwargs.get("actual_at")
        if isinstance(raw_actual, str):
            try:
                actual_at = datetime.fromisoformat(raw_actual)
                if actual_at.tzinfo is not None:
                    actual_at = actual_at.astimezone(timezone.utc).replace(tzinfo=None)
                kwargs["actual_at"] = actual_at
            except (ValueError, TypeError):
                kwargs["actual_at"] = datetime.utcnow()
        elif raw_actual is None:
            kwargs["actual_at"] = datetime.utcnow()

        if kwargs.get("planned_at") and isinstance(kwargs["actual_at"], datetime):
            try:
                planned_hour, planned_minute = str(kwargs["planned_at"]).split(":")[:2]
                planned_at = kwargs["actual_at"].replace(
                    hour=int(planned_hour),
                    minute=int(planned_minute),
                )
                kwargs["time_delta_min"] = int(
                    (kwargs["actual_at"] - planned_at).total_seconds() / 60
                )
            except (ValueError, IndexError, TypeError):
                kwargs["time_delta_min"] = 0

        c = await self.checkin_repo.create_checkin(
            trip_id=trip_id, user_id=user_id,
            poi_type=poi_type, poi_name=poi_name, **kwargs,
        )

        # 更新行程状态
        trip.checked_in = (trip.checked_in or 0) + 1
        if kwargs.get("lat"):
            trip.last_lat = kwargs["lat"]
        if kwargs.get("lng"):
            trip.last_lng = kwargs["lng"]

        # B5: 推进 current_day（当签到 day 大于当前 day 时）
        source_day = kwargs.get("source_day")
        if source_day and trip.current_day and source_day > trip.current_day:
            trip.current_day = source_day

        # 记录花费
        if kwargs.get("actual_cost"):
            cost_actual_at = kwargs.get("actual_at") or datetime.utcnow()
            await self.expense_repo.create_expense(
                trip_id=trip_id, amount=kwargs["actual_cost"],
                category=poi_type_to_category(poi_type),
                checkin_id=c.id, planned_amount=kwargs.get("planned_cost"),
                spent_at=cost_actual_at,
                note=kwargs.get("note"),
            )
            trip.budget_spent = await self.expense_repo.sum_by_trip(trip_id)
            trip.budget_remain = (trip.budget_total or 0) - trip.budget_spent

        await self.trip_repo.update(trip)
        return self._checkin_to_dict(c)

    async def list_checkins(self, trip_id: str, day: int | None = None,
                            page: int = 1, page_size: int = 100) -> PaginatedData:
        offset = (page - 1) * page_size
        checkins = await self.checkin_repo.list_by_trip(trip_id, day, offset, page_size)
        total = await self.checkin_repo.count_by_trip(trip_id)
        return PaginatedData.create(
            [self._checkin_to_dict(c) for c in checkins],
            total=total, page=page, page_size=page_size,
        )

    # ---- Expenses ----

    async def add_expense(self, trip_id: str, amount: float, category: str, **kwargs) -> dict:
        e = await self.expense_repo.create_expense(trip_id=trip_id, amount=amount, category=category, **kwargs)
        trip = await self.trip_repo.get_by_id(e.trip_id)
        if trip:
            trip.budget_spent = await self.expense_repo.sum_by_trip(trip_id)
            trip.budget_remain = (trip.budget_total or 0) - trip.budget_spent
            await self.trip_repo.update(trip)
        return self._expense_to_dict(e)

    async def list_expenses(self, trip_id: str, category: str | None = None) -> list[dict]:
        expenses = await self.expense_repo.list_by_trip(trip_id, category)
        return [self._expense_to_dict(e) for e in expenses]

    # ---- Adjustments ----

    async def create_adjustment(self, trip_id: str, trigger_type: str, **kwargs) -> dict:
        a = await self.adj_repo.create_adjustment(trip_id=trip_id, trigger_type=trigger_type, **kwargs)
        return self._adj_to_dict(a)

    async def list_adjustments(self, trip_id: str, status: str | None = None,
                               page: int = 1, page_size: int = 20) -> PaginatedData:
        offset = (page - 1) * page_size
        adjs = await self.adj_repo.list_by_trip(trip_id, status, offset, page_size)
        total = await self.adj_repo.count_by_trip(trip_id, status)
        return PaginatedData.create(
            [self._adj_to_dict(a) for a in adjs],
            total=total, page=page, page_size=page_size,
        )

    async def accept_adjustment(self, adj_id: str, trip_id: str) -> dict:
        a = await self.adj_repo.get_by_id(adj_id)
        if not a or a.trip_id != trip_id:
            raise ValueError("Adjustment not found")
        a.status = "accepted"
        a.accepted_at = datetime.utcnow()
        await self.adj_repo.update(a)
        return self._adj_to_dict(a)

    async def reject_adjustment(self, adj_id: str, trip_id: str) -> dict:
        a = await self.adj_repo.get_by_id(adj_id)
        if not a or a.trip_id != trip_id:
            raise ValueError("Adjustment not found")
        a.status = "rejected"
        await self.adj_repo.update(a)
        return self._adj_to_dict(a)

    async def apply_adjustment(self, adj_id: str, trip_id: str) -> dict:
        """应用调整 — 更新行程后续内容"""
        a = await self.adj_repo.get_by_id(adj_id)
        if not a or a.trip_id != trip_id:
            raise ValueError("Adjustment not found")
        a.status = "applied"
        await self.adj_repo.update(a)
        # 将 adjusted_plan 合并到 trip_state（实际逻辑由 AdjustAgent 完成）
        return self._adj_to_dict(a)

    async def get_pending_adjustments(self, trip_id: str) -> list[dict]:
        adjs = await self.adj_repo.get_pending(trip_id)
        return [self._adj_to_dict(a) for a in adjs]

    # ---- Serializers ----

    def _trip_to_dict(self, t: TripState) -> dict:
        return {
            "id": t.id, "plan_id": t.plan_id, "user_id": t.user_id,
            "status": t.status, "current_day": t.current_day,
            "total_pois": t.total_pois, "checked_in": t.checked_in,
            "started_at": t.started_at.isoformat() if t.started_at else None,
            "paused_at": t.paused_at.isoformat() if t.paused_at else None,
            "completed_at": t.completed_at.isoformat() if t.completed_at else None,
            "last_lat": t.last_lat, "last_lng": t.last_lng,
            "budget_total": t.budget_total, "budget_spent": t.budget_spent,
            "budget_remain": t.budget_remain,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

    def _checkin_to_dict(self, c: Checkin) -> dict:
        return {
            "id": c.id, "trip_id": c.trip_id,
            "poi_type": c.poi_type, "poi_name": c.poi_name, "poi_id": c.poi_id,
            "source_day": c.source_day,
            "lat": c.lat, "lng": c.lng,
            "photos": c.photos or [],
            "planned_at": c.planned_at,
            "actual_at": c.actual_at.isoformat() if c.actual_at else None,
            "time_delta_min": c.time_delta_min,
            "planned_cost": c.planned_cost, "actual_cost": c.actual_cost,
            "rating": c.rating, "note": c.note,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }

    def _expense_to_dict(self, e: ExpenseRecord) -> dict:
        return {
            "id": e.id, "trip_id": e.trip_id, "checkin_id": e.checkin_id,
            "category": e.category, "amount": e.amount, "planned_amount": e.planned_amount,
            "note": e.note,
            "spent_at": e.spent_at.isoformat() if e.spent_at else None,
        }

    def _adj_to_dict(self, a: Adjustment) -> dict:
        return {
            "id": a.id, "trip_id": a.trip_id,
            "trigger_type": a.trigger_type, "trigger_detail": a.trigger_detail,
            "original_plan": a.original_plan, "adjusted_plan": a.adjusted_plan,
            "reason": a.reason, "status": a.status,
            "accepted_at": a.accepted_at.isoformat() if a.accepted_at else None,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }




    async def _create_plan_from_data(self, user_id: str, plan_id: str,
                                       plan_data: dict) -> Plan:
        """根据 plan_data 创建方案记录（用户不存在则自动创建）"""
        # 确保用户存在（匿名用户可能没有 User 记录）
        from app.db.repositories.user_repo import UserRepository
        user_repo = UserRepository(self.trip_repo.db)
        await user_repo.ensure_development_user(user_id)

        destination = plan_data.get("destination") or plan_data.get("trip_config", {}).get("destination", "未知")
        # 提取 daily_itinerary 数组存入 itinerary 列，与 PlanResponse 期望格式一致
        daily = plan_data.get("daily_itinerary") or plan_data.get("daily_plan", [])
        plan = Plan(
            id=plan_id,
            user_id=user_id,
            destination=destination,
            start_date=date.today(),
            end_date=date.today(),
            budget=float(plan_data.get("total_budget") or plan_data.get("budget", {}).get("total", 0)),
            travelers=int(plan_data.get("people_count") or plan_data.get("trip_config", {}).get("travelers", 1)),
            itinerary=daily,
            status="completed",
        )
        return await self.plan_repo.create(plan)


def _count_pois_from_itinerary(itinerary: Any, budget_total: float) -> tuple[int, float]:
    """从数据库方案 itinerary 中统计打卡点数和预算"""
    total_pois = 0
    if isinstance(itinerary, dict):
        daily = itinerary.get("daily_itinerary") or itinerary.get("daily_plan", [])
    elif isinstance(itinerary, list):
        daily = itinerary
    else:
        daily = []
    for day in daily:
        total_pois += len(day.get("activities") or day.get("attractions", []))
        total_pois += len(day.get("meals", []))
    return total_pois, budget_total


def _get_plan_daily_itinerary(plan: Any) -> list[dict]:
    """兼容读取方案中的每日行程数组。"""
    if not plan:
        return []
    itinerary = getattr(plan, "itinerary", None)
    if isinstance(itinerary, dict):
        daily = itinerary.get("daily_itinerary") or itinerary.get("daily_plan") or []
    elif isinstance(itinerary, list):
        daily = itinerary
    else:
        daily = []
    if not daily:
        full_data = getattr(plan, "full_data", None)
        if isinstance(full_data, dict):
            daily = full_data.get("daily_itinerary") or full_data.get("daily_plan") or []
    return [day for day in daily if isinstance(day, dict)]


def _get_plan_total_days(plan: Any) -> int:
    """从方案行程或日期范围得到总天数，用于保护日推进边界。"""
    if not plan:
        return 0
    daily = _get_plan_daily_itinerary(plan)
    if daily:
        return len(daily)

    start_date = getattr(plan, "start_date", None)
    end_date = getattr(plan, "end_date", None)
    if isinstance(start_date, date) and isinstance(end_date, date) and end_date >= start_date:
        return (end_date - start_date).days + 1
    return 0


def _build_reminder_day_outline(day: dict) -> dict:
    stops = []
    activities = day.get("activities") or day.get("attractions") or []
    for activity in activities:
        if not isinstance(activity, dict):
            continue
        activity_type = activity.get("type") or "attraction"
        if activity_type == "food":
            activity_type = "restaurant"
        time_slot = str(
            activity.get("time_slot")
            or activity.get("planned_time")
            or activity.get("time")
            or "09:00"
        )
        stops.append({
            "type": activity_type,
            "name": activity.get("title") or activity.get("name") or "",
            "planned_time": time_slot.split("-")[0].strip(),
        })
    for meal in day.get("meals") or []:
        if not isinstance(meal, dict):
            continue
        stops.append({
            "type": "restaurant",
            "name": meal.get("restaurant") or meal.get("name") or "",
            "planned_time": meal.get("time") or meal.get("time_slot") or "12:00",
        })
    return {"stops": [stop for stop in stops if stop["name"]]}


def _get_plan_day_weather(plan: Any, day_number: int, day_plan: dict | None = None) -> dict:
    day_plan = day_plan or {}
    forecast = getattr(plan, "weather_forecast", None)
    if not isinstance(forecast, list) or not forecast:
        full_data = getattr(plan, "full_data", None)
        forecast = full_data.get("weather_forecast", []) if isinstance(full_data, dict) else []
    if not isinstance(forecast, list):
        forecast = []

    day_date = str(day_plan.get("date") or "").strip()
    if not day_date:
        start_date = getattr(plan, "start_date", None)
        if isinstance(start_date, date):
            day_date = (start_date + timedelta(days=day_number - 1)).isoformat()

    selected = next((
        item for item in forecast
        if isinstance(item, dict) and day_date and str(item.get("date") or "") == day_date
    ), None)
    if selected is None:
        selected = next((
            item for item in forecast
            if isinstance(item, dict) and _to_int(item.get("day")) == day_number
        ), None)
    if selected is None and 0 <= day_number - 1 < len(forecast):
        indexed = forecast[day_number - 1]
        selected = indexed if isinstance(indexed, dict) else None

    summary_weather = _parse_weather_summary(str(day_plan.get("weather_summary") or ""))
    selected = selected or {}
    return {
        "date": str(selected.get("date") or day_date),
        "condition": str(
            selected.get("weather")
            or selected.get("condition")
            or selected.get("day_weather")
            or summary_weather.get("condition")
            or ""
        ),
        "temp_high": _to_temperature(
            selected.get("temp_high")
            or selected.get("high")
            or summary_weather.get("temp_high")
        ),
        "temp_low": _to_temperature(
            selected.get("temp_low")
            or selected.get("low")
            or summary_weather.get("temp_low")
        ),
        "advice": str(selected.get("advice") or ""),
    }


def _parse_weather_summary(summary: str) -> dict:
    match = re.search(
        r"(?P<condition>[\u4e00-\u9fff]{1,8})?\s*"
        r"(?P<high>-?\d+(?:\.\d+)?)\s*°?C?\s*[/~至-]\s*"
        r"(?P<low>-?\d+(?:\.\d+)?)\s*°?C?",
        summary,
        flags=re.IGNORECASE,
    )
    if not match:
        return {}
    return {
        "condition": (match.group("condition") or "").strip(),
        "temp_high": float(match.group("high")),
        "temp_low": float(match.group("low")),
    }


def _to_temperature(value: Any) -> float | None:
    if value is None or value == "":
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", str(value))
    return float(match.group()) if match else None


def _to_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _count_pois_from_plan_data(data: dict, budget_total: float) -> tuple[int, float]:
    """从前端传来的 plan_data 中统计打卡点数和预算"""
    total_pois = 0
    daily = data.get("daily_itinerary") or data.get("daily_plan", [])
    for day in daily:
        total_pois += len(day.get("activities") or day.get("attractions", []))
        total_pois += len(day.get("meals", []))
    if not budget_total:
        budget_total = float(data.get("total_budget") or data.get("budget", {}).get("total", 0))
    return total_pois, budget_total


def poi_type_to_category(poi_type: str) -> str:
    mapping = {
        "attraction": "门票", "restaurant": "餐饮",
        "hotel": "住宿", "transport": "交通",
        "shopping": "购物", "other": "其他",
    }
    return mapping.get(poi_type, "其他")
