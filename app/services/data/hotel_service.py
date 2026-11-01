"""
酒店基础数据服务
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.hotel import Hotel


class HotelService:
    """酒店数据服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, hotel_id: str) -> Optional[Hotel]:
        result = await self.db.execute(
            select(Hotel).where(Hotel.id == hotel_id)
        )
        return result.scalar_one_or_none()

    async def search_by_city(
        self,
        city: str,
        min_star: int = 0,
        max_price: Optional[float] = None,
        amenity: Optional[str] = None,
        limit: int = 50,
    ) -> list[Hotel]:
        query = select(Hotel).where(Hotel.city == city)
        if min_star:
            query = query.where(Hotel.star >= min_star)
        if max_price:
            query = query.where(Hotel.price_per_night <= max_price)
        if amenity:
            query = query.where(Hotel.amenities.contains([amenity]))
        query = query.order_by(Hotel.rating.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
