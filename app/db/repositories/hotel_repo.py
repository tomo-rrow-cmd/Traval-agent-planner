"""酒店 Repository"""

from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hotel import Hotel
from app.db.repositories.base import BaseRepository


class HotelRepository(BaseRepository[Hotel]):
    """酒店数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(Hotel, db)

    async def search_by_city(
        self,
        city: str,
        min_star: int = 0,
        max_price: Optional[float] = None,
        amenity: Optional[str] = None,
        limit: int = 50,
    ) -> Sequence[Hotel]:
        """按城市搜索酒店，支持星级、价格和设施过滤"""
        query = select(Hotel).where(Hotel.city == city)
        if min_star:
            query = query.where(Hotel.star >= min_star)
        if max_price:
            query = query.where(Hotel.price_per_night <= max_price)
        if amenity:
            query = query.where(Hotel.amenities.contains([amenity]))
        query = query.order_by(Hotel.rating.desc()).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
