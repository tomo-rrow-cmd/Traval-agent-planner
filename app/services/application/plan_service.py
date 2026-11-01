"""旅行方案业务服务"""

from datetime import date, datetime

from app.db.models.plan import Plan
from app.db.repositories.plan_repo import PlanRepository
from app.db.repositories.user_repo import UserRepository
from app.exceptions import NotFoundException
from app.schemas.common import PaginatedData
from app.schemas.plan import (
    PlanDraftRequest,
    PlanFavoriteResult,
    PlanFromDataRequest,
    PlanResponse,
    PlanSaveResult,
    PlanShareRequest,
    PlanShareResult,
    PlanSummary,
)


class TravelPlanService:
    """封装旅行方案创建、查询和列表用例"""

    def __init__(
        self,
        plan_repository: PlanRepository,
        user_repository: UserRepository | None = None,
    ):
        self.plan_repository = plan_repository
        self.user_repository = user_repository

    async def create_plan(
        self,
        user_id: str,
        request: PlanDraftRequest,
    ) -> PlanResponse:
        """创建旅行方案任务（契约 MVP 的持久化占位）"""
        if self.user_repository is not None:
            await self.user_repository.ensure_development_user(user_id)

        start_date = request.start_date or date.today()
        end_date = request.end_date or start_date
        plan = await self.plan_repository.create_for_user(
            user_id=user_id,
            destination=request.destination,
            start_date=start_date,
            end_date=end_date,
            budget=request.budget,
            travelers=request.travelers,
            preferences=request.preferences,
            status="generating",
        )
        return self._to_response(plan)

    async def get_plan(self, user_id: str, plan_id: str) -> PlanResponse:
        """获取用户自己的方案详情"""
        plan = await self.plan_repository.get_by_id_for_user(
            plan_id=plan_id,
            user_id=user_id,
        )
        if plan is None:
            raise NotFoundException("Travel plan not found")
        return self._to_response(plan)

    async def list_plans(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        saved_only: bool = False,
    ) -> PaginatedData[PlanSummary]:
        """分页查询用户方案列表"""
        offset = (page - 1) * page_size
        plans = await self.plan_repository.list_by_user(
            user_id=user_id,
            offset=offset,
            limit=page_size,
            status=status,
            saved_only=saved_only,
        )
        total = await self.plan_repository.count_by_user(user_id, status=status, saved_only=saved_only)
        return PaginatedData.create(
            [self._to_summary(plan) for plan in plans],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def delete_plan(self, user_id: str, plan_id: str) -> dict:
        """删除用户自己的方案"""
        plan = await self.plan_repository.get_by_id_for_user(
            plan_id=plan_id,
            user_id=user_id,
        )
        if plan is None:
            raise NotFoundException("Plan not found")
        await self.plan_repository.delete(plan, soft=False)
        return {}

    async def share_plan(
        self,
        user_id: str,
        plan_id: str,
        request: PlanShareRequest,
    ) -> PlanShareResult:
        """生成分享链接占位结果"""
        await self.get_plan(user_id=user_id, plan_id=plan_id)
        expire_at = None
        if request.expire_in:
            expire_at = datetime.utcnow()
        return PlanShareResult(
            share_url=f"https://travel.example.com/s/{plan_id}",
            expire_at=expire_at,
        )

    async def create_plan_from_data(
        self,
        user_id: str,
        data: PlanFromDataRequest,
    ) -> PlanResponse:
        """从本地缓存数据创建方案，并标记为已保存"""
        if self.user_repository is not None:
            await self.user_repository.ensure_development_user(user_id)
        start_date = data.start_date or date.today()
        end_date = data.end_date or start_date
        plan = await self.plan_repository.create_for_user(
            user_id=user_id,
            destination=data.destination or data.title or "未命名",
            start_date=start_date,
            end_date=end_date,
            budget=data.budget,
            travelers=data.travelers or 1,
            preferences=data.preferences or [],
            status="completed",
            departure=data.departure,
            crowd_type=data.crowd_type,
            travel_style=data.travel_style,
        )
        # 如果有 full_data，写入各 JSON 列
        if data.full_data:
            await self.plan_repository.update_full_data(plan.id, data.full_data)
        # 标记为已保存
        plan.saved_at = datetime.utcnow()
        await self.plan_repository.db.flush()
        return self._to_response(plan)

    async def save_plan(self, user_id: str, plan_id: str) -> PlanSaveResult:
        """用户主动保存方案，标记 saved_at"""
        plan = await self.plan_repository.mark_as_saved(plan_id, user_id)
        if plan is None:
            raise NotFoundException("Travel plan not found")
        return PlanSaveResult(
            id=plan.id,
            saved_at=plan.saved_at,
        )

    async def toggle_favorite(self, user_id: str, plan_id: str) -> PlanFavoriteResult:
        """收藏切换：真实持久化到数据库"""
        plan = await self.plan_repository.get_by_id_for_user(plan_id, user_id)
        if plan is None:
            raise NotFoundException("Travel plan not found")
        current = bool(plan.is_favorite) if isinstance(plan.is_favorite, dict) else bool(plan.is_favorite)
        plan.is_favorite = {"active": not current}
        await self.plan_repository.db.flush()
        return PlanFavoriteResult(is_favorite=not current)

    def _to_summary(self, plan: Plan) -> PlanSummary:
        """转换 ORM 模型为方案摘要"""
        days = 0
        if plan.start_date and plan.end_date:
            days = (plan.end_date - plan.start_date).days + 1
        return PlanSummary(
            id=plan.id,
            title=f"{plan.destination}旅行方案" if plan.destination else "未命名旅行方案",
            destination=plan.destination,
            start_date=plan.start_date,
            end_date=plan.end_date,
            days=max(days, 0),
            estimated_cost=plan.total_cost or 0,
            travel_style=plan.travel_style,
            status=plan.status,
            is_favorite=bool(plan.is_favorite) if isinstance(plan.is_favorite, dict) else bool(plan.is_favorite),
            saved_at=plan.saved_at,
            created_at=plan.created_at,
        )

    def _to_response(
        self,
        plan: Plan,
    ) -> PlanResponse:
        """转换 ORM 模型为 API 响应结构

        优先使用独立列（overview / traffic_summary 等），
        若独立列为空则从 full_data（final_plan 原始 JSON）构建。
        """
        days = 0
        if plan.start_date and plan.end_date:
            days = (plan.end_date - plan.start_date).days + 1

        # 读取 itinerary：兼容旧格式（list）和新格式（dict 含 daily_itinerary）
        itinerary = plan.itinerary or []
        if isinstance(itinerary, dict):
            itinerary = itinerary.get("daily_itinerary", [])

        for day_data in itinerary:
            if not isinstance(day_data, dict):
                continue
            if "attractions" in day_data and "activities" not in day_data:
                day_data["activities"] = day_data.pop("attractions")
            for activity in day_data.get("activities", []):
                if not isinstance(activity, dict):
                    continue
                if "title" not in activity and "name" in activity:
                    activity["title"] = activity["name"]
                if "time_slot" not in activity and "time" in activity:
                    activity["time_slot"] = activity["time"]
                if not activity.get("location"):
                    coordinates = activity.get("coordinates") or activity
                    lat = coordinates.get("lat", coordinates.get("latitude"))
                    lng = coordinates.get("lng", coordinates.get("longitude"))
                    if lat is not None and lng is not None:
                        activity["location"] = {"lat": lat, "lng": lng}
                if isinstance(activity.get("tags"), str):
                    activity["tags"] = (
                        [activity["tags"]] if activity["tags"] else []
                    )
            for meal in day_data.get("meals", []):
                if (
                    isinstance(meal, dict)
                    and "time_slot" not in meal
                    and "time" in meal
                ):
                    meal["time_slot"] = meal["time"]

        travel_style = plan.travel_style or ""
        fd = plan.full_data or {}

        # 归一化 hotel_plan 坐标：flat latitude/longitude → location: {lat, lng}
        # 同时过滤掉坐标为 None 的推荐，避免前端 Number(null)→0 放置到 (0,0)
        hotel_plan_raw = plan.hotel_plan or fd.get("hotel_plan", {})
        if isinstance(hotel_plan_raw, dict):
            normalized_recs = []
            for rec in hotel_plan_raw.get("recommendations", []) or []:
                if not isinstance(rec, dict):
                    continue
                lat = rec.get("lat", rec.get("latitude"))
                lng = rec.get("lng", rec.get("longitude"))
                if lat is None or lng is None:
                    continue
                rec_normalized = {**rec, "location": {"lat": lat, "lng": lng}}
                normalized_recs.append(rec_normalized)
            # 同步归一化 selected_hotel
            selected = hotel_plan_raw.get("selected_hotel")
            if isinstance(selected, dict):
                slat = selected.get("lat", selected.get("latitude"))
                slng = selected.get("lng", selected.get("longitude"))
                if slat is not None and slng is not None:
                    selected = {**selected, "location": {"lat": slat, "lng": slng}}
                else:
                    selected = None
            hotel_plan = {
                **hotel_plan_raw,
                "recommendations": normalized_recs,
                "selected_hotel": selected or hotel_plan_raw.get("selected_hotel"),
            }
        else:
            hotel_plan = hotel_plan_raw

        return PlanResponse(
            id=plan.id,
            title=f"{plan.destination}旅行方案" if plan.destination else "未命名旅行方案",
            destination=plan.destination,
            departure=plan.departure or fd.get("origin") or fd.get("departure") or "",
            start_date=plan.start_date,
            end_date=plan.end_date,
            days=max(days, 0),
            people_count=plan.travelers or 1,
            crowd_type=plan.crowd_type or fd.get("crowd_type") or "",
            total_budget=plan.budget or 0,
            estimated_cost=plan.total_cost or 0,
            travel_style=travel_style,
            status=plan.status,
            version=plan.version or 1,
            is_favorite=(
                plan.is_favorite.get("active", False)
                if isinstance(plan.is_favorite, dict)
                else bool(plan.is_favorite)
            ),
            saved_at=plan.saved_at,
            view_count=plan.view_count or 0,
            overview=plan.overview or _build_overview(fd),
            daily_itinerary=itinerary,
            traffic_summary=plan.traffic_summary or _build_traffic_summary(fd),
            food_summary=plan.food_summary or _build_food_summary(fd),
            budget_detail=plan.budget_detail or _build_budget_detail(fd),
            souvenir_recommendations=(
                plan.souvenir_recommendations
                or fd.get("souvenirs", fd.get("souvenir_recommendations", []))
            ),
            weather_forecast=plan.weather_forecast or fd.get("weather_forecast", []),
            packing_list=plan.packing_list or fd.get("packing_list", []),
            tips=plan.tips or fd.get("tips", []),
            avoid_list=plan.avoid_list or fd.get("avoid_list", []),
            created_at=plan.created_at,
            updated_at=plan.updated_at,

            # ====== 前端 PlanPreview/PlanDetailPage 直接读取的原始数据 ======
            traffic=fd.get("traffic", {}),
            hotel_plan=hotel_plan,
            big_traffic=(
                plan.big_traffic
                if isinstance(plan.big_traffic, list) and plan.big_traffic
                else ([fd.get("big_traffic")] if isinstance(fd.get("big_traffic"), dict) and fd.get("big_traffic") else (fd.get("big_traffic") or []))
            ),
            budget=fd.get("budget", {}),
            meal_plan=plan.meal_plan or fd.get("meal_plan", []),
            attraction_details=plan.attraction_details or fd.get("attraction_details", []),
            food_details=plan.food_details or fd.get("food_details", []),
            weather_impact=fd.get("weather_impact", []),
            per_person_per_day=fd.get("budget", {}).get("per_person_per_day", 0),
            pace=(plan.travel_style or fd.get("trip_config", {}).get("pace", "") or fd.get("pace", "")),
            full_data=fd,
        )


# ============================================================
# 辅助函数：从 full_data（final_plan 原始 JSON）构建结构化字段
# ============================================================


def _build_overview(fd: dict) -> dict:
    """从 full_data 构建 overview"""
    if fd.get("overview") and isinstance(fd["overview"], dict):
        return fd["overview"]
    highlights = fd.get("highlights", [])
    traffic = fd.get("traffic", {})
    daily_traffic = traffic.get("daily_traffic", [])
    total_distance = 0
    modes = set()
    for dt in daily_traffic:
        for seg in dt.get("segments", []):
            total_distance += seg.get("distance_km", 0) or 0
            if seg.get("mode"):
                modes.add(seg["mode"])
    return {
        "highlights": highlights if isinstance(highlights, list) else [],
        "total_distance_km": round(total_distance, 1),
        "transport_modes": sorted(modes),
    }


def _build_traffic_summary(fd: dict) -> dict:
    """从 full_data 构建 traffic_summary"""
    if fd.get("traffic_summary") and isinstance(fd["traffic_summary"], dict):
        return fd["traffic_summary"]
    traffic = fd.get("traffic", {})
    bt = fd.get("big_traffic", [])
    if isinstance(bt, dict):
        bt = [bt]
    city_to_city = []
    for entry in bt:
        for t in (entry.get("trains") or [])[:3]:
            ps = t.get("prices", {})
            first_price = next(iter(ps.values()), None) if isinstance(ps, dict) else None
            city_to_city.append({
                "mode": "火车",
                "from": t.get("fromStationName", ""),
                "to": t.get("toStationName", ""),
                "price": first_price,
                "duration": t.get("duration", ""),
                "recommendation": f"{t.get('trainCode', '')} {t.get('departureTime', '')}-{t.get('arrivalTime', '')}",
            })
    return {
        "city_to_city": city_to_city,
        "city_internal": traffic.get("summary", ""),
        "total_traffic_cost": traffic.get("total_traffic_cost", 0),
    }


def _build_food_summary(fd: dict) -> dict:
    """从 full_data 构建 food_summary"""
    if fd.get("food_summary") and isinstance(fd["food_summary"], dict):
        return fd["food_summary"]
    meal_plan = fd.get("meal_plan", [])
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


def _build_budget_detail(fd: dict) -> dict:
    """从 full_data 构建 budget_detail"""
    if fd.get("budget_detail") and isinstance(fd["budget_detail"], dict):
        return fd["budget_detail"]
    budget = fd.get("budget", {})
    details = budget.get("details", [])
    total_budget = budget.get("total_budget", fd.get("total_budget", 0))
    actual_total = budget.get("actual_total", fd.get("estimated_cost", 0))
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
        for d in details:
            if d.get("category") in names:
                spent = d.get("spent", 0)
                break
        breakdown[key] = {"amount": spent, "percent": round(spent / total_budget * 100, 1) if total_budget > 0 else 0, "items": []}
    return {
        "total": float(total_budget),
        "actual_total": float(actual_total),
        "remaining": float(budget.get("remaining", max(float(total_budget) - float(actual_total), 0))),
        "breakdown": breakdown,
        "warnings": budget.get("warnings", []),
        "suggestions": budget.get("suggestions", []),
        "per_person_per_day": budget.get("per_person_per_day", 0),
    }
