"""补 service 层缺口 — 正确 mock 签名"""

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestHotelService:
    @pytest.mark.asyncio
    async def test_search_by_city_empty(self):
        from app.services.data.hotel_service import HotelService
        db = AsyncMock()
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        db.execute.return_value = r
        svc = HotelService(db)
        result = await svc.search_by_city("北京")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_by_city_with_filters(self):
        from app.services.data.hotel_service import HotelService
        db = AsyncMock()
        r = MagicMock()
        r.scalars.return_value.all.return_value = []
        db.execute.return_value = r
        svc = HotelService(db)
        result = await svc.search_by_city("上海", min_star=4, max_price=500, amenity="wifi", limit=10)
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_id(self):
        from app.services.data.hotel_service import HotelService
        db = AsyncMock()
        r = MagicMock()
        r.scalar_one_or_none.return_value = None
        db.execute.return_value = r
        svc = HotelService(db)
        result = await svc.get_by_id("hotel-1")
        assert result is None


class TestPlanService:
    @pytest.mark.asyncio
    async def test_list_user_plans_empty(self):
        from app.services.application.plan_service import TravelPlanService
        repo = MagicMock()
        repo.list_by_user = AsyncMock(return_value=[])
        repo.count_by_user = AsyncMock(return_value=0)
        svc = TravelPlanService(repo)
        result = await svc.list_plans("user-1")
        assert result.list == []

    @pytest.mark.asyncio
    async def test_get_plan_not_found(self):
        from app.services.application.plan_service import TravelPlanService
        from app.exceptions import NotFoundException
        repo = MagicMock()
        repo.get_by_id_for_user = AsyncMock(return_value=None)
        svc = TravelPlanService(repo)
        with pytest.raises(NotFoundException):
            await svc.get_plan("user-1", "plan-1")

    @pytest.mark.asyncio
    async def test_delete_plan_not_found(self):
        from app.services.application.plan_service import TravelPlanService
        from app.exceptions import NotFoundException
        repo = MagicMock()
        repo.get_by_id_for_user = AsyncMock(return_value=None)
        svc = TravelPlanService(repo)
        with pytest.raises(NotFoundException):
            await svc.delete_plan("user-1", "plan-1")


class TestUserService:
    @pytest.mark.asyncio
    async def test_get_profile_existing(self):
        from app.services.application.user_service import UserService
        mock_user = MagicMock()
        mock_user.id = "u1"
        mock_user.username = "tester"
        mock_user.avatar = None
        mock_user.created_at = None
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=mock_user)
        svc = UserService(repo)
        result = await svc.get_profile("u1")
        assert result.id == "u1"
        assert result.nickname == "tester"

    @pytest.mark.asyncio
    async def test_get_profile_not_found_returns_default(self):
        from app.services.application.user_service import UserService
        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)
        svc = UserService(repo)
        result = await svc.get_profile("unknown")
        assert result.nickname == "旅行者"
