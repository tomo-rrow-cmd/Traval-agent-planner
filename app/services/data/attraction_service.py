"""
景点基础数据服务 - 景点数据的 CRUD 与查询
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attraction import Attraction


class AttractionService:
    """景点数据服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, attraction_id: str) -> Optional[Attraction]:
        result = await self.db.execute(
            select(Attraction).where(Attraction.id == attraction_id)
        )
        return result.scalar_one_or_none()

    async def search_by_city(
        self,
        city: str,
        category: Optional[str] = None,
        min_rating: float = 0,
        limit: int = 50,
    ) -> list[Attraction]:
        query = select(Attraction).where(Attraction.city == city)
        if category:
            query = query.where(Attraction.category == category)
        if min_rating:
            query = query.where(Attraction.rating >= min_rating)
        query = query.order_by(Attraction.rating.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def search_by_tags(
        self,
        city: str,
        tags: list[str],
        limit: int = 50,
    ) -> list[Attraction]:
        """根据标签搜索景点"""
        # 使用 JSON 包含查询
        query = (
            select(Attraction)
            .where(Attraction.city == city)
            .where(Attraction.tags.contains(tags))
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_top_rated(
        self,
        city: str,
        limit: int = 10,
    ) -> list[Attraction]:
        """获取城市评分最高的景点"""
        query = (
            select(Attraction)
            .where(Attraction.city == city)
            .order_by(Attraction.rating.desc())
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())
