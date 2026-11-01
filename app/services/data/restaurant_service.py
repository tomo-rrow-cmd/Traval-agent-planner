"""
餐厅基础数据服务
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.restaurant import Restaurant


class RestaurantService:
    """餐厅数据服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, restaurant_id: str) -> Optional[Restaurant]:
        result = await self.db.execute(
            select(Restaurant).where(Restaurant.id == restaurant_id)
        )
        return result.scalar_one_or_none()

    async def search_by_city(
        self,
        city: str,
        cuisine: Optional[str] = None,
        max_price: Optional[float] = None,
        min_rating: float = 0,
        limit: int = 50,
    ) -> list[Restaurant]:
        query = select(Restaurant).where(Restaurant.city == city)
        if cuisine:
            query = query.where(Restaurant.cuisine == cuisine)
        if max_price:
            query = query.where(Restaurant.avg_price <= max_price)
        if min_rating:
            query = query.where(Restaurant.rating >= min_rating)
        query = query.order_by(Restaurant.rating.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search_by_tags(
        self,
        city: str,
        tags: list[str],
        limit: int = 50,
    ) -> list[Restaurant]:
        query = (
            select(Restaurant)
            .where(Restaurant.city == city)
            .where(Restaurant.tags.contains(tags))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
