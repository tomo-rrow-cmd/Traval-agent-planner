"""测试 app/services/application/trip_service.py — TripService"""

import socket
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import date, datetime
from types import SimpleNamespace

from app.services.application.trip_service import (
    TripService,
    _build_reminder_day_outline,
    _count_pois_from_itinerary,
    _count_pois_from_plan_data,
    _get_plan_daily_itinerary,
    _get_plan_day_weather,
    _get_plan_total_days,
    poi_type_to_category,
)
from app.schemas.common import PaginatedData


@pytest.fixture(autouse=True)
def block_external_network(monkeypatch):
    def fail_external_connection(*_args, **_kwargs):
        raise AssertionError("unit tests must not access external services or databases")

    monkeypatch.setattr(socket.socket, "connect", fail_external_connection)
    monkeypatch.setattr(socket, "create_connection", fail_external_connection)


# Mock repository factory
def make_mock_repo(**methods):
    """创建一个 mock repository，可覆盖特定方法"""
    repo = MagicMock()
    for name, val in methods.items():
        setattr(repo, name, val)
    return repo


@pytest.fixture
def trip_repo():
    return make_mock_repo(
        create_for_plan=AsyncMock(),
        get_by_id_for_user=AsyncMock(),
        list_by_user=AsyncMock(return_value=[]),
        count_by_user=AsyncMock(return_value=0),
        get_by_id=AsyncMock(return_value=None),
        update=AsyncMock(),
    )


@pytest.fixture
def checkin_repo():
    return make_mock_repo(
        create_checkin=AsyncMock(),
        list_by_trip=AsyncMock(return_value=[]),
        count_by_trip=AsyncMock(return_value=0),
        get_by_trip_and_poi=AsyncMock(return_value=None),
    )


@pytest.fixture
def expense_repo():
    return make_mock_repo(
        create_expense=AsyncMock(),
        list_by_trip=AsyncMock(return_value=[]),
        sum_by_trip=AsyncMock(return_value=0),
    )


@pytest.fixture
def adj_repo():
    return make_mock_repo(
        create_adjustment=AsyncMock(),
        list_by_trip=AsyncMock(return_value=[]),
        count_by_trip=AsyncMock(return_value=0),
        get_by_id=AsyncMock(),
        update=AsyncMock(),
        get_pending=AsyncMock(return_value=[]),
    )


@pytest.fixture
def service(trip_repo, checkin_repo, expense_repo, adj_repo):
    return TripService(trip_repo, checkin_repo, expense_repo, adj_repo)


# ═══════════════════════════════════════════════════════
# poi_type_to_category
# ═══════════════════════════════════════════════════════

class TestPoiTypeToCategory:
    def test_known_types(self):
        assert poi_type_to_category("attraction") == "门票"
        assert poi_type_to_category("restaurant") == "餐饮"
        assert poi_type_to_category("hotel") == "住宿"
        assert poi_type_to_category("transport") == "交通"
        assert poi_type_to_category("shopping") == "购物"
        assert poi_type_to_category("other") == "其他"

    def test_unknown_type_falls_back_to_other(self):
        assert poi_type_to_category("invalid") == "其他"
        assert poi_type_to_category("") == "其他"


# ═══════════════════════════════════════════════════════
# Basic CRUD
# ═══════════════════════════════════════════════════════

class TestStartTrip:
    @pytest.mark.asyncio
    async def test_creates_trip_and_returns_dict(self, service, trip_repo):
        mock_trip = MagicMock()
        mock_trip.id = "trip-1"
        mock_trip.plan_id = "plan-1"
        mock_trip.user_id = "user-1"
        mock_trip.status = "active"
        mock_trip.current_day = 1
        mock_trip.total_pois = 10
        mock_trip.checked_in = 0
        mock_trip.budget_total = 5000
        mock_trip.budget_spent = 0
        mock_trip.budget_remain = 5000
        mock_trip.last_lat = None
        mock_trip.last_lng = None
        mock_trip.started_at = datetime(2026, 7, 14)
        mock_trip.paused_at = None
        mock_trip.completed_at = None
        mock_trip.created_at = datetime(2026, 7, 14)
        mock_trip.updated_at = datetime(2026, 7, 14)

        trip_repo.create_for_plan.return_value = mock_trip

        # Set up plan_repo so the "plan exists in DB" path is taken
        mock_plan = MagicMock()
        mock_plan.itinerary = None
        mock_plan.budget = None
        mock_plan_repo = MagicMock()
        mock_plan_repo.get_by_id = AsyncMock(return_value=mock_plan)
        service.plan_repo = mock_plan_repo

        result = await service.start_trip("user-1", "plan-1", 5000)
        assert result["id"] == "trip-1"
        assert result["status"] == "active"
        assert result["budget_total"] == 5000


class TestGetTrip:
    @pytest.mark.asyncio
    async def test_existing_trip_returns_dict(self, service, trip_repo):
        mock_trip = MagicMock()
        mock_trip.id = "trip-1"
        mock_trip.user_id = "user-1"
        mock_trip.status = "active"
        mock_trip.current_day = 1
        mock_trip.total_pois = 0
        mock_trip.checked_in = 0
        mock_trip.budget_total = 0
        mock_trip.budget_spent = 0
        mock_trip.budget_remain = 0
        mock_trip.last_lat = None
        mock_trip.last_lng = None
        mock_trip.started_at = None
        mock_trip.paused_at = None
        mock_trip.completed_at = None
        mock_trip.created_at = None
        mock_trip.updated_at = None

        trip_repo.get_by_id_for_user.return_value = mock_trip

        result = await service.get_trip("trip-1", "user-1")
        assert result is not None
        assert result["id"] == "trip-1"

    @pytest.mark.asyncio
    async def test_nonexistent_trip_returns_none(self, service, trip_repo):
        trip_repo.get_by_id_for_user.return_value = None
        result = await service.get_trip("missing", "user-1")
        assert result is None


class TestAdvanceDay:
    @pytest.mark.asyncio
    async def test_advances_before_last_day(self, service, trip_repo):
        trip = MagicMock(
            id="trip-1", plan_id="plan-1", status="active", current_day=2,
        )
        plan = MagicMock(itinerary=[{"day": 1}, {"day": 2}, {"day": 3}])
        plan_repo = MagicMock(get_by_id=AsyncMock(return_value=plan))
        service.plan_repo = plan_repo
        trip_repo.get_by_id_for_user.return_value = trip

        await service.advance_day("trip-1", "user-1")

        assert trip.current_day == 3
        trip_repo.update.assert_awaited_once_with(trip)

    @pytest.mark.asyncio
    async def test_rejects_advancing_past_last_day(self, service, trip_repo):
        trip = MagicMock(
            id="trip-1", plan_id="plan-1", status="active", current_day=3,
        )
        plan = MagicMock(itinerary=[{"day": 1}, {"day": 2}, {"day": 3}])
        plan_repo = MagicMock(get_by_id=AsyncMock(return_value=plan))
        service.plan_repo = plan_repo
        trip_repo.get_by_id_for_user.return_value = trip

        with pytest.raises(ValueError, match="最后一天"):
            await service.advance_day("trip-1", "user-1")

        trip_repo.update.assert_not_awaited()


class TestReminderContext:
    @pytest.mark.asyncio
    async def test_last_day_does_not_create_tomorrow(self, service, trip_repo):
        trip = MagicMock(plan_id="plan-1", current_day=3)
        plan = MagicMock(
            destination="北京",
            itinerary=[{"day": 1}, {"day": 2}, {"day": 3}],
            full_data={},
        )
        service.plan_repo = MagicMock(get_by_id=AsyncMock(return_value=plan))
        trip_repo.get_by_id_for_user.return_value = trip

        context = await service.get_reminder_context("trip-1", "user-1")

        assert context["is_last_day"] is True
        assert context["total_days"] == 3
        assert "tomorrow_day" not in context
        assert context["day_outline"] == {"stops": []}

    @pytest.mark.asyncio
    async def test_uses_real_next_day_itinerary(self, service, trip_repo):
        trip = MagicMock(plan_id="plan-1", current_day=1)
        plan = MagicMock(
            destination="北京",
            itinerary=[
                {"day": 1, "activities": [{"title": "玉渊潭公园"}]},
                {
                    "day": 2,
                    "activities": [{
                        "title": "故宫博物院",
                        "type": "attraction",
                        "time_slot": "08:30-11:30",
                    }],
                    "meals": [{"restaurant": "四季民福", "time": "12:00"}],
                },
                {"day": 3, "activities": [{"title": "中国美术馆"}]},
            ],
            full_data={},
            weather_forecast=[],
        )
        service.plan_repo = MagicMock(get_by_id=AsyncMock(return_value=plan))
        trip_repo.get_by_id_for_user.return_value = trip

        context = await service.get_reminder_context("trip-1", "user-1")

        assert context["is_last_day"] is False
        assert context["tomorrow_day"] == 2
        assert context["destination"] == "北京"
        assert context["day_outline"]["stops"] == [
            {"type": "attraction", "name": "故宫博物院", "planned_time": "08:30"},
            {"type": "restaurant", "name": "四季民福", "planned_time": "12:00"},
        ]

    @pytest.mark.parametrize(
        ("forecast", "day_plan", "expected"),
        [
            (
                [{"date": "2026-07-19", "weather": "多云", "temp_high": 32, "temp_low": 22}],
                {"date": "2026-07-19"},
                ("多云", 32, 22),
            ),
            (
                [{"day": 2, "weather": "小雨", "temp_high": 24, "temp_low": 19}],
                {},
                ("小雨", 24, 19),
            ),
            (
                [
                    {"weather": "晴", "temp_high": 30, "temp_low": 20},
                    {"weather": "阴", "temp_high": 27, "temp_low": 18},
                ],
                {},
                ("阴", 27, 18),
            ),
            (
                [],
                {"weather_summary": "多云 32°C / 22°C"},
                ("多云", 32, 22),
            ),
        ],
    )
    def test_weather_uses_plan_data_without_defaults(self, forecast, day_plan, expected):
        from app.services.application.trip_service import _get_plan_day_weather

        plan = MagicMock(weather_forecast=forecast, full_data={}, start_date=None)
        weather = _get_plan_day_weather(plan, 2, day_plan)

        assert (weather["condition"], weather["temp_high"], weather["temp_low"]) == expected


class TestTravelogueContext:
    @pytest.mark.asyncio
    async def test_aggregates_plan_checkins_and_actual_expenses(
        self, service, trip_repo, checkin_repo, expense_repo,
    ):
        trip = MagicMock(
            id="trip-1", plan_id="plan-1", status="completed", current_day=3,
            budget_spent=188.0,
        )
        plan = MagicMock(
            destination="北京",
            start_date=datetime(2026, 7, 17).date(),
            end_date=datetime(2026, 7, 19).date(),
            itinerary=[{"day": 1}, {"day": 2}, {"day": 3}],
            full_data={},
        )
        checkin = MagicMock(
            id="checkin-1", trip_id="trip-1", poi_type="attraction",
            poi_name="故宫博物院", poi_id=None, source_day=2,
            lat=None, lng=None, photos=[], planned_at="08:30",
            actual_at=datetime(2026, 7, 18, 8, 40), time_delta_min=10,
            planned_cost=60, actual_cost=60, rating=5, note="很震撼",
            created_at=datetime(2026, 7, 18, 8, 40),
        )
        expense = MagicMock(
            id="expense-1", trip_id="trip-1", checkin_id="checkin-1",
            category="门票", amount=60, planned_amount=60, note="故宫门票",
            spent_at=datetime(2026, 7, 18, 8, 40),
        )
        service.plan_repo = MagicMock(get_by_id=AsyncMock(return_value=plan))
        trip_repo.get_by_id_for_user.return_value = trip
        checkin_repo.list_by_trip.return_value = [checkin]
        expense_repo.list_by_trip.return_value = [expense]

        context = await service.get_travelogue_context("trip-1", "user-1")

        assert context["destination"] == "北京"
        assert context["total_days"] == 3
        assert context["actual_total_cost"] == 60
        assert context["checkins"][0]["note"] == "很震撼"
        assert context["checkins"][0]["source_day"] == 2


class TestListTrips:
    @pytest.mark.asyncio
    async def test_returns_paginated_data(self, service, trip_repo):
        mock_trip = MagicMock()
        mock_trip.id = "t-1"
        mock_trip.user_id = "u-1"
        mock_trip.status = "active"
        mock_trip.current_day = 1
        mock_trip.total_pois = 0
        mock_trip.checked_in = 0
        mock_trip.budget_total = 0
        mock_trip.budget_spent = 0
        mock_trip.budget_remain = 0
        mock_trip.last_lat = None
        mock_trip.last_lng = None
        mock_trip.started_at = None
        mock_trip.paused_at = None
        mock_trip.completed_at = None
        mock_trip.created_at = None
        mock_trip.updated_at = None

        trip_repo.list_by_user.return_value = [mock_trip]
        trip_repo.count_by_user.return_value = 1

        result = await service.list_trips("user-1", page=2, page_size=10)
        assert isinstance(result, PaginatedData)
        assert len(result.list) == 1
        assert result.page == 2
        assert result.page_size == 10
        assert result.total == 1


# ═══════════════════════════════════════════════════════
# Status transitions
# ═══════════════════════════════════════════════════════

class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_valid_transition_active_to_paused(self, service, trip_repo):
        mock_trip = MagicMock()
        mock_trip.status = "active"
        trip_repo.get_by_id_for_user.return_value = mock_trip

        result = await service.update_status("t1", "user-1", "paused")
        assert mock_trip.status == "paused"
        trip_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_valid_transition_paused_to_active(self, service, trip_repo):
        mock_trip = MagicMock()
        mock_trip.status = "paused"
        trip_repo.get_by_id_for_user.return_value = mock_trip

        result = await service.update_status("t1", "user-1", "active")
        assert mock_trip.status == "active"
        assert mock_trip.paused_at is None  # 清除暂停时间

    @pytest.mark.asyncio
    async def test_invalid_transition_unchanged(self, service, trip_repo):
        mock_trip = MagicMock()
        mock_trip.status = "active"
        trip_repo.get_by_id_for_user.return_value = mock_trip

        result = await service.update_status("t1", "user-1", "completed")
        assert mock_trip.status == "completed"

    @pytest.mark.asyncio
    async def test_trip_not_found_raises(self, service, trip_repo):
        trip_repo.get_by_id_for_user.return_value = None
        with pytest.raises(ValueError, match="Trip not found"):
            await service.update_status("bad", "user-1", "active")


# ═══════════════════════════════════════════════════════
# Checkin
# ═══════════════════════════════════════════════════════

class TestCheckin:
    @pytest.mark.asyncio
    async def test_checkin_without_cost(self, service, trip_repo, checkin_repo):
        mock_trip = MagicMock()
        mock_trip.status = "active"
        mock_trip.checked_in = 0
        mock_trip.budget_total = 5000
        mock_trip.budget_spent = 0
        mock_trip.budget_remain = 5000
        trip_repo.get_by_id_for_user.return_value = mock_trip

        mock_checkin = MagicMock()
        mock_checkin.id = "c-1"
        checkin_repo.create_checkin.return_value = mock_checkin

        result = await service.checkin("t1", "user-1", "attraction", "故宫")
        assert result["id"] == "c-1"
        assert mock_trip.checked_in == 1

    @pytest.mark.asyncio
    async def test_checkin_with_cost_creates_expense(self, service, trip_repo, checkin_repo, expense_repo):
        mock_trip = MagicMock()
        mock_trip.status = "active"
        mock_trip.checked_in = 0
        mock_trip.budget_total = 5000
        mock_trip.budget_spent = 0
        mock_trip.budget_remain = 5000
        trip_repo.get_by_id_for_user.return_value = mock_trip

        mock_checkin = MagicMock()
        mock_checkin.id = "c-2"
        checkin_repo.create_checkin.return_value = mock_checkin

        expense_repo.sum_by_trip.return_value = 200
        checkin_repo.create_checkin.return_value = mock_checkin

        result = await service.checkin(
            "t1", "user-1", "restaurant", "全聚德",
            actual_cost=200, planned_cost=150, lat=39.9, lng=116.4,
        )

        # 创建了花费记录
        expense_repo.create_expense.assert_called_once()
        # 更新了坐标
        assert mock_trip.last_lat == 39.9
        assert mock_trip.last_lng == 116.4
        # 更新了 budget
        assert mock_trip.budget_spent == 200

    @pytest.mark.asyncio
    async def test_checkin_trip_not_found_raises(self, service, trip_repo):
        trip_repo.get_by_id_for_user.return_value = None
        with pytest.raises(ValueError, match="Trip not found"):
            await service.checkin("bad", "user-1", "attraction", "X")

    @pytest.mark.asyncio
    async def test_checkin_paused_trip_raises(self, service, trip_repo):
        """暂停状态的行程不能签到"""
        mock_trip = MagicMock()
        mock_trip.status = "paused"
        trip_repo.get_by_id_for_user.return_value = mock_trip

        with pytest.raises(ValueError, match="当前行程状态为.*paused"):
            await service.checkin("t1", "user-1", "attraction", "故宫")

    @pytest.mark.asyncio
    async def test_checkin_duplicate_raises(self, service, trip_repo, checkin_repo):
        """同一 POI 重复签到应拒绝"""
        mock_trip = MagicMock()
        mock_trip.status = "active"
        trip_repo.get_by_id_for_user.return_value = mock_trip

        # mock 返回已存在的签到记录
        checkin_repo.get_by_trip_and_poi.return_value = MagicMock()

        with pytest.raises(ValueError, match="已签到过了"):
            await service.checkin("t1", "user-1", "attraction", "故宫")

    @pytest.mark.asyncio
    async def test_checkin_calculates_time_delta(self, service, trip_repo, checkin_repo):
        """签到带 planned_at 时应自动计算 time_delta_min"""
        import datetime

        mock_trip = MagicMock()
        mock_trip.status = "active"
        mock_trip.checked_in = 0
        mock_trip.budget_total = 5000
        mock_trip.budget_spent = 0
        mock_trip.budget_remain = 5000
        trip_repo.get_by_id_for_user.return_value = mock_trip

        now = datetime.datetime(2026, 7, 16, 9, 30, 0)  # 09:30 签到
        mock_checkin = MagicMock()
        mock_checkin.id = "c-3"
        checkin_repo.create_checkin.return_value = mock_checkin

        result = await service.checkin(
            "t1", "user-1", "attraction", "故宫",
            actual_at=now, planned_at="09:00",  # 计划 09:00，实际 09:30 → +30min
        )

        # 验证 create_checkin 的调用参数中包含正确的 time_delta_min
        call_kwargs = checkin_repo.create_checkin.call_args[1]
        assert call_kwargs.get("time_delta_min") == 30


# ═══════════════════════════════════════════════════════
# Adjustments
# ═══════════════════════════════════════════════════════

class TestAdjustments:
    @pytest.mark.asyncio
    async def test_accept_adjustment(self, service, adj_repo):
        mock_adj = MagicMock()
        mock_adj.id = "adj-1"
        mock_adj.trip_id = "t1"
        mock_adj.status = "pending"
        adj_repo.get_by_id.return_value = mock_adj

        result = await service.accept_adjustment("adj-1", "t1")
        assert result["status"] == "accepted"
        adj_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_accept_wrong_trip_raises(self, service, adj_repo):
        mock_adj = MagicMock()
        mock_adj.trip_id = "t2"  # wrong trip
        adj_repo.get_by_id.return_value = mock_adj

        with pytest.raises(ValueError, match="Adjustment not found"):
            await service.accept_adjustment("adj-1", "t1")

    @pytest.mark.asyncio
    async def test_reject_adjustment(self, service, adj_repo):
        mock_adj = MagicMock()
        mock_adj.id = "adj-1"
        mock_adj.trip_id = "t1"
        adj_repo.get_by_id.return_value = mock_adj

        result = await service.reject_adjustment("adj-1", "t1")
        assert result["status"] == "rejected"
        adj_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_apply_adjustment(self, service, adj_repo):
        mock_adj = MagicMock()
        mock_adj.id = "adj-1"
        mock_adj.trip_id = "t1"
        adj_repo.get_by_id.return_value = mock_adj

        result = await service.apply_adjustment("adj-1", "t1")
        assert result["status"] == "applied"

    @pytest.mark.asyncio
    async def test_get_pending_adjustments(self, service, adj_repo):
        mock_adj = MagicMock()
        mock_adj.id = "adj-1"
        mock_adj.trip_id = "t1"
        adj_repo.get_pending.return_value = [mock_adj]

        result = await service.get_pending_adjustments("t1")
        assert len(result) == 1
        assert result[0]["id"] == "adj-1"


def _trip_record(**overrides):
    values = {
        "id": "trip-1",
        "plan_id": "plan-1",
        "user_id": "user-1",
        "status": "active",
        "current_day": 1,
        "total_pois": 0,
        "checked_in": 0,
        "started_at": None,
        "paused_at": None,
        "completed_at": None,
        "last_lat": None,
        "last_lng": None,
        "budget_total": 0,
        "budget_spent": 0,
        "budget_remain": 0,
        "created_at": None,
        "updated_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _checkin_record(**overrides):
    values = {
        "id": "checkin-1",
        "trip_id": "trip-1",
        "poi_type": "attraction",
        "poi_name": "故宫",
        "poi_id": None,
        "source_day": 1,
        "lat": None,
        "lng": None,
        "photos": None,
        "planned_at": None,
        "actual_at": None,
        "time_delta_min": 0,
        "planned_cost": None,
        "actual_cost": None,
        "rating": None,
        "note": None,
        "created_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _expense_record(**overrides):
    values = {
        "id": "expense-1",
        "trip_id": "trip-1",
        "checkin_id": None,
        "category": "餐饮",
        "amount": 88.5,
        "planned_amount": 80,
        "note": "午餐",
        "spent_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _adjustment_record(**overrides):
    values = {
        "id": "adjustment-1",
        "trip_id": "trip-1",
        "trigger_type": "weather",
        "trigger_detail": {},
        "original_plan": {},
        "adjusted_plan": {},
        "reason": "下雨",
        "status": "pending",
        "accepted_at": None,
        "created_at": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TestTripServiceCoverageEdges:
    @pytest.mark.asyncio
    async def test_start_trip_counts_database_plan_and_uses_plan_budget(
        self, service, trip_repo,
    ):
        plan = SimpleNamespace(
            itinerary={
                "daily_itinerary": [{
                    "activities": [{"name": "故宫"}, {"name": "景山"}],
                    "meals": [{"restaurant": "四季民福"}],
                }],
            },
            budget=1200,
        )
        service.plan_repo = MagicMock(get_by_id=AsyncMock(return_value=plan))
        trip_repo.create_for_plan.return_value = _trip_record(
            total_pois=3, budget_total=1200, budget_remain=1200,
        )

        result = await service.start_trip("user-1", "plan-1")

        assert result["total_pois"] == 3
        trip_repo.create_for_plan.assert_awaited_once_with(
            "user-1", "plan-1", budget_total=1200.0, total_pois=3,
        )

    @pytest.mark.asyncio
    async def test_start_trip_creates_missing_plan_from_payload(
        self, service, trip_repo,
    ):
        plan_repo = MagicMock(
            get_by_id=AsyncMock(return_value=None),
            create=AsyncMock(side_effect=lambda plan: plan),
        )
        service.plan_repo = plan_repo
        trip_repo.db = MagicMock()
        trip_repo.create_for_plan.return_value = _trip_record(
            plan_id="new-plan", total_pois=2, budget_total=900, budget_remain=900,
        )
        user_repo = MagicMock(ensure_development_user=AsyncMock())
        plan_data = {
            "trip_config": {"destination": "苏州", "travelers": 2},
            "daily_plan": [{
                "attractions": [{"name": "拙政园"}],
                "meals": [{"restaurant": "松鹤楼"}],
            }],
            "budget": {"total": 900},
        }

        with patch(
            "app.db.repositories.user_repo.UserRepository",
            return_value=user_repo,
        ):
            result = await service.start_trip(
                "user-1", "new-plan", plan_data=plan_data,
            )

        created_plan = plan_repo.create.await_args.args[0]
        assert result["total_pois"] == 2
        assert created_plan.destination == "苏州"
        assert created_plan.travelers == 2
        assert created_plan.budget == 900
        user_repo.ensure_development_user.assert_awaited_once_with("user-1")

    @pytest.mark.asyncio
    async def test_start_trip_rejects_missing_plan(self, service):
        service.plan_repo = MagicMock(get_by_id=AsyncMock(return_value=None))

        with pytest.raises(ValueError, match="方案不存在"):
            await service.start_trip("user-1", "missing")

    @pytest.mark.asyncio
    async def test_progress_returns_budget_and_location(self, service, trip_repo, expense_repo):
        trip_repo.get_by_id_for_user.return_value = _trip_record(
            checked_in=3,
            total_pois=4,
            budget_total=1000,
            last_lat=39.9,
            last_lng=116.4,
        )
        expense_repo.sum_by_trip.return_value = 250.25

        result = await service.get_progress("trip-1", "user-1")

        assert result["progress_pct"] == 75.0
        assert result["budget_remain"] == 749.75
        assert result["last_location"] == {"lat": 39.9, "lng": 116.4}

        trip_repo.get_by_id_for_user.return_value = None
        with pytest.raises(ValueError, match="Trip not found"):
            await service.get_progress("missing", "user-1")

    @pytest.mark.asyncio
    async def test_advance_day_rejects_missing_and_inactive_trips(self, service, trip_repo):
        trip_repo.get_by_id_for_user.return_value = None
        with pytest.raises(ValueError, match="Trip not found"):
            await service.advance_day("missing", "user-1")

        trip_repo.get_by_id_for_user.return_value = _trip_record(status="paused")
        with pytest.raises(ValueError, match="无法推进天数"):
            await service.advance_day("trip-1", "user-1")

    @pytest.mark.asyncio
    async def test_context_methods_reject_missing_trip(self, service, trip_repo):
        trip_repo.get_by_id_for_user.return_value = None

        with pytest.raises(ValueError, match="Trip not found"):
            await service.get_reminder_context("missing", "user-1")
        with pytest.raises(ValueError, match="Trip not found"):
            await service.get_travelogue_context("missing", "user-1")

    @pytest.mark.asyncio
    async def test_checkin_normalizes_timezone_and_advances_day(
        self, service, trip_repo, checkin_repo,
    ):
        trip = _trip_record(current_day=1)
        trip_repo.get_by_id_for_user.return_value = trip
        checkin_repo.create_checkin.return_value = _checkin_record(source_day=2)

        await service.checkin(
            "trip-1",
            "user-1",
            "attraction",
            "故宫",
            actual_at="2026-07-16T09:30:00+08:00",
            planned_at="01:00",
            source_day=2,
        )

        call_kwargs = checkin_repo.create_checkin.await_args.kwargs
        assert call_kwargs["actual_at"] == datetime(2026, 7, 16, 1, 30)
        assert call_kwargs["time_delta_min"] == 30
        assert trip.current_day == 2

    @pytest.mark.asyncio
    async def test_checkin_falls_back_for_invalid_times(
        self, service, trip_repo, checkin_repo,
    ):
        trip_repo.get_by_id_for_user.return_value = _trip_record()
        checkin_repo.create_checkin.return_value = _checkin_record()

        await service.checkin(
            "trip-1",
            "user-1",
            "attraction",
            "故宫",
            actual_at="not-a-date",
            planned_at="invalid",
        )

        call_kwargs = checkin_repo.create_checkin.await_args.kwargs
        assert isinstance(call_kwargs["actual_at"], datetime)
        assert call_kwargs["time_delta_min"] == 0

    @pytest.mark.asyncio
    async def test_checkin_and_expense_lists_are_serialized(
        self, service, checkin_repo, expense_repo,
    ):
        checkin_repo.list_by_trip.return_value = [
            _checkin_record(actual_at=datetime(2026, 7, 16, 9, 30)),
        ]
        checkin_repo.count_by_trip.return_value = 1
        expense_repo.list_by_trip.return_value = [
            _expense_record(spent_at=datetime(2026, 7, 16, 12, 0)),
        ]

        checkins = await service.list_checkins(
            "trip-1", day=2, page=2, page_size=10,
        )
        expenses = await service.list_expenses("trip-1", "餐饮")

        assert checkins.total == 1
        assert checkins.page == 2
        assert checkins.list[0]["actual_at"] == "2026-07-16T09:30:00"
        assert expenses[0]["spent_at"] == "2026-07-16T12:00:00"
        checkin_repo.list_by_trip.assert_awaited_once_with("trip-1", 2, 10, 10)

    @pytest.mark.asyncio
    async def test_add_expense_updates_existing_trip_only(
        self, service, trip_repo, expense_repo,
    ):
        expense = _expense_record()
        expense_repo.create_expense.return_value = expense
        expense_repo.sum_by_trip.return_value = 188.5
        trip = _trip_record(budget_total=500)
        trip_repo.get_by_id.return_value = trip

        result = await service.add_expense("trip-1", 88.5, "餐饮", note="午餐")

        assert result["amount"] == 88.5
        assert trip.budget_spent == 188.5
        assert trip.budget_remain == 311.5
        trip_repo.update.assert_awaited_once_with(trip)

        trip_repo.get_by_id.return_value = None
        await service.add_expense("trip-1", 20, "交通")
        assert trip_repo.update.await_count == 1

    @pytest.mark.asyncio
    async def test_adjustment_create_list_and_missing_mutations(self, service, adj_repo):
        adjustment = _adjustment_record()
        adj_repo.create_adjustment.return_value = adjustment
        adj_repo.list_by_trip.return_value = [adjustment]
        adj_repo.count_by_trip.return_value = 1

        created = await service.create_adjustment(
            "trip-1", "weather", reason="下雨",
        )
        listed = await service.list_adjustments(
            "trip-1", status="pending", page=2, page_size=5,
        )

        assert created["reason"] == "下雨"
        assert listed.total == 1
        adj_repo.list_by_trip.assert_awaited_once_with("trip-1", "pending", 5, 5)

        adj_repo.get_by_id.return_value = None
        with pytest.raises(ValueError, match="Adjustment not found"):
            await service.reject_adjustment("missing", "trip-1")
        with pytest.raises(ValueError, match="Adjustment not found"):
            await service.apply_adjustment("missing", "trip-1")


class TestTripServiceHelperEdges:
    def test_itinerary_helpers_accept_legacy_and_invalid_shapes(self):
        legacy = {
            "daily_plan": [{
                "attractions": [{"name": "拙政园"}],
                "meals": [{"restaurant": "松鹤楼"}],
            }],
        }

        assert _count_pois_from_itinerary(legacy, 300) == (2, 300)
        assert _count_pois_from_itinerary("invalid", 300) == (0, 300)
        assert _get_plan_daily_itinerary(None) == []
        assert _get_plan_daily_itinerary(SimpleNamespace(itinerary=legacy)) == legacy["daily_plan"]
        assert _get_plan_daily_itinerary(
            SimpleNamespace(
                itinerary="invalid",
                full_data={"daily_itinerary": [{"day": 1}, "invalid"]},
            ),
        ) == [{"day": 1}]

    def test_total_days_uses_dates_when_itinerary_is_empty(self):
        plan = SimpleNamespace(
            itinerary=None,
            full_data={},
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 3),
        )

        assert _get_plan_total_days(None) == 0
        assert _get_plan_total_days(plan) == 3
        plan.end_date = date(2026, 6, 30)
        assert _get_plan_total_days(plan) == 0

    def test_reminder_outline_filters_invalid_items_and_normalizes_food(self):
        result = _build_reminder_day_outline({
            "activities": [
                "invalid",
                {"type": "food", "name": "早餐店", "planned_time": "08:00"},
                {"type": "attraction", "name": ""},
            ],
            "meals": ["invalid", {"name": "午餐店", "time_slot": "12:30"}],
        })

        assert result == {"stops": [
            {"type": "restaurant", "name": "早餐店", "planned_time": "08:00"},
            {"type": "restaurant", "name": "午餐店", "planned_time": "12:30"},
        ]}

    def test_weather_and_payload_helpers_cover_fallbacks(self):
        plan = SimpleNamespace(
            weather_forecast="invalid",
            full_data={"weather_forecast": "invalid"},
            start_date=date(2026, 7, 1),
        )

        weather = _get_plan_day_weather(plan, 2)
        count, budget = _count_pois_from_plan_data({
            "daily_plan": [{
                "activities": [{"name": "故宫"}],
                "meals": [{"restaurant": "四季民福"}],
            }],
            "total_budget": 600,
        }, 0)

        assert weather == {
            "date": "2026-07-02",
            "condition": "",
            "temp_high": None,
            "temp_low": None,
            "advice": "",
        }
        assert (count, budget) == (2, 600.0)
