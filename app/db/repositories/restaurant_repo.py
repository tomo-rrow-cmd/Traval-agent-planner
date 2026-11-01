"""餐厅 Repository"""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.restaurant import Restaurant
from app.db.repositories.base import BaseRepository


class RestaurantRepository(BaseRepository[Restaurant]):
    """餐厅数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(Restaurant, db)

    async def search_by_city(
        self,
        city: str,
        cuisine: Optional[str] = None,
        max_price: Optional[float] = None,
        min_rating: float = 0,
        limit: int = 50,
    ) -> Sequence[Restaurant]:
        """按城市搜索餐厅，支持菜系、价格和评分过滤"""
        query = select(Restaurant).where(Restaurant.city == city)
        if cuisine:
            query = query.where(Restaurant.cuisine == cuisine)
        if max_price:
            query = query.where(Restaurant.avg_price <= max_price)
        if min_rating:
            query = query.where(Restaurant.rating >= min_rating)
        query = query.order_by(Restaurant.rating.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_by_tags(
        self,
        city: str,
        tags: list[str],
        limit: int = 50,
    ) -> Sequence[Restaurant]:
        """按标签搜索餐厅"""
        query = (
            select(Restaurant)
            .where(Restaurant.city == city)
            .where(Restaurant.tags.contains(tags))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
