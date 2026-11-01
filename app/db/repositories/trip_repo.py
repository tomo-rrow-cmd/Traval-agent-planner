"""行程执行 Repository"""

from datetime import datetime
from typing import Sequence

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.trip import TripState, Checkin, ExpenseRecord, Adjustment
from app.db.repositories.base import BaseRepository


class TripRepository(BaseRepository[TripState]):
    """行程状态数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(TripState, db)

    async def create_for_plan(self, user_id: str, plan_id: str,
                              budget_total: float = 0, total_pois: int = 0) -> TripState:
        trip = TripState(
            plan_id=plan_id, user_id=user_id,
            status="active", total_pois=total_pois,
            budget_total=budget_total,
            budget_remain=budget_total, budget_spent=0,
            started_at=datetime.utcnow(),
        )
        return await self.create(trip)

    async def get_active_for_user(self, user_id: str) -> TripState | None:
        result = await self.db.execute(
            select(TripState).where(
                TripState.user_id == user_id,
                TripState.status.in_(["active", "paused"]),
            ).order_by(TripState.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str, status: str | None = None,
                           offset: int = 0, limit: int = 20) -> Sequence[TripState]:
        query = select(TripState).where(TripState.user_id == user_id)
        if status:
            query = query.where(TripState.status == status)
        query = query.order_by(TripState.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: str, status: str | None = None) -> int:
        return await self.count(user_id=user_id, status=status)

    async def get_by_id_for_user(self, trip_id: str, user_id: str) -> TripState | None:
        result = await self.db.execute(
            select(TripState).where(TripState.id == trip_id, TripState.user_id == user_id)
        )
        return result.scalar_one_or_none()


class CheckinRepository(BaseRepository[Checkin]):
    """签到记录数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(Checkin, db)

    async def create_checkin(self, trip_id: str, user_id: str, **kwargs) -> Checkin:
        c = Checkin(trip_id=trip_id, user_id=user_id, **kwargs)
        return await self.create(c)

    async def list_by_trip(self, trip_id: str, day: int | None = None,
                           offset: int = 0, limit: int = 100) -> Sequence[Checkin]:
        query = select(Checkin).where(Checkin.trip_id == trip_id)
        if day is not None:
            query = query.where(Checkin.source_day == day)
        query = query.order_by(Checkin.actual_at.asc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_by_trip_and_poi(self, trip_id: str, poi_name: str) -> Checkin | None:
        result = await self.db.execute(
            select(Checkin).where(
                Checkin.trip_id == trip_id, Checkin.poi_name == poi_name
            ).order_by(Checkin.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def count_by_trip(self, trip_id: str) -> int:
        return await self.count(trip_id=trip_id)


class ExpenseRepository(BaseRepository[ExpenseRecord]):
    """花费记录数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(ExpenseRecord, db)

    async def create_expense(self, trip_id: str, amount: float, category: str, **kwargs) -> ExpenseRecord:
        e = ExpenseRecord(trip_id=trip_id, amount=amount, category=category, **kwargs)
        return await self.create(e)

    async def list_by_trip(self, trip_id: str, category: str | None = None,
                           offset: int = 0, limit: int = 200) -> Sequence[ExpenseRecord]:
        query = select(ExpenseRecord).where(ExpenseRecord.trip_id == trip_id)
        if category:
            query = query.where(ExpenseRecord.category == category)
        query = query.order_by(ExpenseRecord.spent_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def sum_by_trip(self, trip_id: str) -> float:
        result = await self.db.execute(
            select(func.coalesce(func.sum(ExpenseRecord.amount), 0.0))
            .where(ExpenseRecord.trip_id == trip_id)
        )
        return result.scalar_one()


class AdjustmentRepository(BaseRepository[Adjustment]):
    """调整记录数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(Adjustment, db)

    async def create_adjustment(self, trip_id: str, trigger_type: str,
                                reason: str = "", **kwargs) -> Adjustment:
        a = Adjustment(trip_id=trip_id, trigger_type=trigger_type, reason=reason, **kwargs)
        return await self.create(a)

    async def list_by_trip(self, trip_id: str, status: str | None = None,
                           offset: int = 0, limit: int = 50) -> Sequence[Adjustment]:
        query = select(Adjustment).where(Adjustment.trip_id == trip_id)
        if status:
            query = query.where(Adjustment.status == status)
        query = query.order_by(Adjustment.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_pending(self, trip_id: str) -> Sequence[Adjustment]:
        return await self.list_by_trip(trip_id, status="pending")

    async def count_by_trip(self, trip_id: str, status: str | None = None) -> int:
        return await self.count(trip_id=trip_id, status=status)
