"""补 plan.py + user.py 剩余缺口"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import date
from httpx import AsyncClient, ASGITransport
from app.api.router import app
from app.dependencies import get_current_user, get_plan_service


@pytest.mark.asyncio
async def test_delete_plan():
    """DELETE /plans/{id} — 删除方案"""
    async def override_user():
        return {"user_id": "u1", "phone": "13800138000"}

    mock_svc = MagicMock()
    mock_svc.delete_plan = AsyncMock(return_value={})

    async def override_plan_service():
        return mock_svc

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_plan_service] = override_plan_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.delete("/api/v1/plans/p1")

        assert resp.status_code == 200
        assert resp.json()["code"] == 0
        assert resp.json()["data"] == {}
        mock_svc.delete_plan.assert_awaited_once_with(user_id="u1", plan_id="p1")
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_toggle_favorite():
    """POST /plans/{id}/favorites — 收藏切换"""
    async def override_user():
        return {"user_id": "u1", "phone": "13800138000"}

    from app.schemas.plan import PlanFavoriteResult
    mock_svc = MagicMock()
    mock_svc.get_plan = AsyncMock()
    mock_svc.toggle_favorite = AsyncMock(return_value=PlanFavoriteResult(is_favorite=True))

    async def override_plan_service():
        return mock_svc

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_plan_service] = override_plan_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/plans/p1/favorites")

        assert resp.status_code == 200
        assert resp.json()["data"] == {"is_favorite": True}
        mock_svc.toggle_favorite.assert_awaited_once_with(
            user_id="u1",
            plan_id="p1",
        )
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_share_plan():
    """POST /plans/{id}/shares — 分享方案"""
    async def override_user():
        return {"user_id": "u1", "phone": "13800138000"}

    from app.schemas.plan import PlanShareResult
    mock_svc = MagicMock()
    mock_svc.get_plan = AsyncMock()
    mock_svc.share_plan = AsyncMock(return_value=PlanShareResult(
        share_url="https://travel.example.com/s/p1", expire_at=None,
    ))

    async def override_plan_service():
        return mock_svc

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_plan_service] = override_plan_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post("/api/v1/plans/p1/shares", json={})

        assert resp.status_code == 200
        assert resp.json()["data"] == {
            "share_url": "https://travel.example.com/s/p1",
            "expire_at": None,
        }
        mock_svc.share_plan.assert_awaited_once()
        assert mock_svc.share_plan.await_args.kwargs["user_id"] == "u1"
        assert mock_svc.share_plan.await_args.kwargs["plan_id"] == "p1"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_profile():
    """GET /user/profile — 获取用户资料"""
    async def override_user():
        return {"user_id": "u1", "phone": "13800138000"}

    from app.dependencies import get_user_service
    mock_svc = MagicMock()
    mock_svc.get_profile = AsyncMock(return_value=MagicMock(
        id="u1", nickname="tester", phone=None, avatar_url=None, created_at=None,
    ))

    async def override_user_service():
        return mock_svc

    app.dependency_overrides[get_current_user] = override_user
    app.dependency_overrides[get_user_service] = override_user_service
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/v1/user/profile")

        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == "u1"
        assert resp.json()["data"]["nickname"] == "tester"
        mock_svc.get_profile.assert_awaited_once_with("u1")
    finally:
        app.dependency_overrides.clear()


class TestUserServiceGaps:
    @pytest.mark.asyncio
    async def test_get_profile_user_not_found(self):
        """get_profile: user=None → 返回默认 profile"""
        from app.services.application.user_service import UserService
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        svc = UserService(repo)
        result = await svc.get_profile("unknown")
        assert result.nickname == "旅行者"

    @pytest.mark.asyncio
    async def test_get_preferences_user_none(self):
        """get_preferences: user=None → 返回空 UserPreferences"""
        from app.services.application.user_service import UserService
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        svc = UserService(repo)
        result = await svc.get_preferences("unknown")
        assert result is not None


class TestPlanServiceGaps:
    def test_to_summary_no_dates(self):
        """_to_summary: start_date=None → days=0"""
        from app.services.application.plan_service import TravelPlanService
        plan = MagicMock()
        plan.id = "p"
        plan.destination = "test"
        plan.start_date = None
        plan.end_date = None
        plan.total_cost = 0
        plan.travel_style = None
        plan.status = "generating"
        plan.is_favorite = False
        plan.saved_at = None
        plan.created_at = None
        svc = TravelPlanService(MagicMock())
        summary = svc._to_summary(plan)
        assert summary.days == 0

    @pytest.mark.asyncio
    async def test_share_plan_service(self):
        """plan_service.share_plan"""
        from app.services.application.plan_service import TravelPlanService
        from app.schemas.plan import PlanShareRequest
        mock_plan = MagicMock()
        mock_plan.id = "p1"
        mock_plan.destination = "北京"
        mock_plan.departure = None
        mock_plan.start_date = None
        mock_plan.end_date = None
        mock_plan.travelers = 1
        mock_plan.crowd_type = None
        mock_plan.budget = 5000
        mock_plan.total_cost = 0
        mock_plan.travel_style = None
        mock_plan.status = "generating"
        mock_plan.version = 1
        mock_plan.is_favorite = False
        mock_plan.saved_at = None
        mock_plan.view_count = 0
        mock_plan.overview = None
        mock_plan.itinerary = []
        mock_plan.traffic_summary = {}
        mock_plan.food_summary = {}
        mock_plan.budget_detail = {}
        mock_plan.souvenir_recommendations = []
        mock_plan.weather_forecast = []
        mock_plan.packing_list = []
        mock_plan.tips = []
        mock_plan.avoid_list = []
        mock_plan.created_at = None
        mock_plan.updated_at = None
        mock_plan.full_data = {}
        mock_plan.hotel_plan = {}
        mock_plan.big_traffic = []
        mock_plan.meal_plan = []
        mock_plan.attraction_details = []
        mock_plan.food_details = []

        repo = MagicMock()
        repo.get_by_id_for_user = AsyncMock(return_value=mock_plan)
        svc = TravelPlanService(repo)
        result = await svc.share_plan("u1", "p1", PlanShareRequest())
        assert "travel.example.com" in result.share_url


class TestPlanServiceHelpers:
    def test_to_response_preserves_map_coordinates_and_meals(self):
        from app.services.application.plan_service import TravelPlanService

        plan = MagicMock()
        plan.id = "map-plan"
        plan.destination = "北京"
        plan.departure = "上海"
        plan.start_date = date(2026, 8, 1)
        plan.end_date = date(2026, 8, 1)
        plan.travelers = 1
        plan.crowd_type = None
        plan.budget = 1000
        plan.total_cost = 500
        plan.travel_style = None
        plan.status = "completed"
        plan.version = 1
        plan.is_favorite = False
        plan.saved_at = None
        plan.view_count = 0
        plan.overview = None
        plan.itinerary = [{
            "day": 1,
            "attractions": [{
                "name": "故宫",
                "type": "attraction",
                "latitude": 39.916,
                "longitude": 116.397,
            }],
            "meals": [{
                "meal": "午餐",
                "restaurant": "测试餐厅",
                "latitude": 39.91,
                "longitude": 116.41,
            }],
        }]
        plan.traffic_summary = {}
        plan.food_summary = {}
        plan.budget_detail = {}
        plan.souvenir_recommendations = []
        plan.weather_forecast = []
        plan.packing_list = []
        plan.tips = []
        plan.avoid_list = []
        plan.created_at = None
        plan.updated_at = None
        plan.full_data = {}
        plan.hotel_plan = {}
        plan.big_traffic = []
        plan.meal_plan = []
        plan.attraction_details = []
        plan.food_details = []

        response = TravelPlanService(MagicMock())._to_response(plan)

        assert response.daily_itinerary[0].activities[0].location.lat == 39.916
        assert response.daily_itinerary[0].activities[0].location.lng == 116.397
        assert response.daily_itinerary[0].meals[0]["restaurant"] == "测试餐厅"
        assert response.daily_itinerary[0].meals[0]["latitude"] == 39.91

    def test_to_response_days_calculation(self):
        from app.services.application.plan_service import TravelPlanService
        plan = MagicMock()
        plan.id = "p1"
        plan.destination = "北京"
        plan.departure = None
        plan.start_date = date(2026, 8, 1)
        plan.end_date = date(2026, 8, 5)  # 5 days
        plan.travelers = 2
        plan.crowd_type = None
        plan.budget = 5000
        plan.total_cost = 3000
        plan.travel_style = None
        plan.status = "completed"
        plan.version = 1
        plan.is_favorite = False
        plan.saved_at = None
        plan.view_count = 0
        plan.overview = None
        plan.itinerary = []
        plan.traffic_summary = {}
        plan.food_summary = {}
        plan.budget_detail = {}
        plan.souvenir_recommendations = []
        plan.weather_forecast = []
        plan.packing_list = []
        plan.tips = []
        plan.avoid_list = []
        plan.created_at = None
        plan.updated_at = None
        plan.full_data = {}
        plan.hotel_plan = {}
        plan.big_traffic = []
        plan.meal_plan = []
        plan.attraction_details = []
        plan.food_details = []

        svc = TravelPlanService(MagicMock())
        resp = svc._to_response(plan)
        assert resp.days == 5

    def test_to_summary_days_calculation(self):
        from app.services.application.plan_service import TravelPlanService
        plan = MagicMock()
        plan.id = "p2"
        plan.destination = "上海"
        plan.start_date = date(2026, 9, 1)
        plan.end_date = date(2026, 9, 3)
        plan.total_cost = 2000
        plan.travel_style = None
        plan.status = "generating"
        plan.is_favorite = False
        plan.saved_at = None
        plan.created_at = None

        svc = TravelPlanService(MagicMock())
        summary = svc._to_summary(plan)
        assert summary.days == 3
        assert summary.destination == "上海"

    def test_to_response_no_dates(self):
        from app.services.application.plan_service import TravelPlanService
        plan = MagicMock()
        plan.id = "p3"
        plan.destination = ""
        plan.departure = None
        plan.start_date = None
        plan.end_date = None
        plan.travelers = 1
        plan.crowd_type = None
        plan.budget = 0
        plan.total_cost = 0
        plan.travel_style = None
        plan.status = "draft"
        plan.version = 1
        plan.is_favorite = False
        plan.saved_at = None
        plan.view_count = 0
        plan.overview = None
        plan.itinerary = []
        plan.traffic_summary = {}
        plan.food_summary = {}
        plan.budget_detail = {}
        plan.souvenir_recommendations = []
        plan.weather_forecast = []
        plan.packing_list = []
        plan.tips = []
        plan.avoid_list = []
        plan.created_at = None
        plan.updated_at = None
        plan.full_data = {}
        plan.hotel_plan = {}
        plan.big_traffic = []
        plan.meal_plan = []
        plan.attraction_details = []
        plan.food_details = []

        svc = TravelPlanService(MagicMock())
        resp = svc._to_response(plan)
        assert resp.days == 0


class TestUserServiceHelpers:
    def test_to_profile(self):
        from app.services.application.user_service import UserService
        user = MagicMock()
        user.id = "u1"
        user.username = "测试用户"
        user.avatar = None
        user.created_at = None

        svc = UserService(MagicMock())
        profile = svc._to_profile(user)
        assert profile.id == "u1"
        assert profile.nickname == "测试用户"
