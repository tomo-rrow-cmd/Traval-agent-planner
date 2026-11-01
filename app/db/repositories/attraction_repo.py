"""景点 Repository"""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attraction import Attraction
from app.db.repositories.base import BaseRepository


class AttractionRepository(BaseRepository[Attraction]):
    """景点数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(Attraction, db)

    async def search_by_city(
        self,
        city: str,
        category: Optional[str] = None,
        min_rating: float = 0,
        limit: int = 50,
    ) -> Sequence[Attraction]:
        """按城市搜索景点，支持分类和评分过滤"""
        query = select(Attraction).where(Attraction.city == city)
        if category:
            query = query.where(Attraction.category == category)
        if min_rating:
            query = query.where(Attraction.rating >= min_rating)
        query = query.order_by(Attraction.rating.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def search_by_tags(
        self,
        city: str,
        tags: list[str],
        limit: int = 50,
    ) -> Sequence[Attraction]:
        """按标签搜索景点"""
        query = (
            select(Attraction)
            .where(Attraction.city == city)
            .where(Attraction.tags.contains(tags))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_top_rated(
        self,
        city: str,
        limit: int = 10,
    ) -> Sequence[Attraction]:
        """获取城市评分最高的景点"""
        query = (
            select(Attraction)
            .where(Attraction.city == city)
            .order_by(Attraction.rating.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return result.scalars().all()
