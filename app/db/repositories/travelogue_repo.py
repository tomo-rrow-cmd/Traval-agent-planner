"""游记 & 社交素材 & 分享 Repository"""

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.travelogue import Travelogue, SocialMaterial, Share
from app.db.repositories.base import BaseRepository


class TravelogueRepository(BaseRepository[Travelogue]):
    """游记数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(Travelogue, db)

    async def create_for_trip(self, trip_id: str, user_id: str, **kwargs) -> Travelogue:
        t = Travelogue(trip_id=trip_id, user_id=user_id, **kwargs)
        return await self.create(t)

    async def get_by_trip(self, trip_id: str) -> Travelogue | None:
        result = await self.db.execute(
            select(Travelogue)
            .where(Travelogue.trip_id == trip_id)
            .order_by(Travelogue.updated_at.desc(), Travelogue.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str | None = None, status: str | None = None,
                           offset: int = 0, limit: int = 20) -> Sequence[Travelogue]:
        query = select(Travelogue)
        if user_id:
            query = query.where(Travelogue.user_id == user_id)
        if status:
            query = query.where(Travelogue.status == status)
        elif not user_id:
            # 公开列表默认只显示已发布/已分享的
            query = query.where(Travelogue.status.in_(["published", "shared"]))
        query = query.order_by(Travelogue.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_by_user(self, user_id: str | None = None) -> int:
        if user_id:
            return await self.count(user_id=user_id)
        return await self.count(status="published") + await self.count(status="shared")

    async def delete_by_id(self, travelogue_id: str) -> bool:
        t = await self.get_by_id(travelogue_id)
        if not t:
            return False
        await self.delete(t)
        return True


class SocialMaterialRepository(BaseRepository[SocialMaterial]):
    """社交素材数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(SocialMaterial, db)

    async def create_material(self, trip_id: str, user_id: str, **kwargs) -> SocialMaterial:
        m = SocialMaterial(trip_id=trip_id, user_id=user_id, is_generated=True, **kwargs)
        return await self.create(m)

    async def list_by_trip(self, trip_id: str, type: str | None = None,
                           offset: int = 0, limit: int = 100) -> Sequence[SocialMaterial]:
        query = select(SocialMaterial).where(SocialMaterial.trip_id == trip_id)
        if type:
            query = query.where(SocialMaterial.type == type)
        query = query.order_by(SocialMaterial.source_day.asc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_favorites(self, user_id: str) -> Sequence[SocialMaterial]:
        query = select(SocialMaterial).where(
            SocialMaterial.user_id == user_id,
            SocialMaterial.is_favorite == True,
        ).order_by(SocialMaterial.created_at.desc())
        result = await self.db.execute(query)
        return result.scalars().all()


class ShareRepository(BaseRepository[Share]):
    """分享链接数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(Share, db)

    async def create_share(self, user_id: str, target_type: str, target_id: str,
                           share_code: str, password: str | None = None,
                           expire_at=None) -> Share:
        s = Share(user_id=user_id, target_type=target_type, target_id=target_id,
                  share_code=share_code, password=password, expire_at=expire_at)
        return await self.create(s)

    async def get_by_code(self, share_code: str) -> Share | None:
        result = await self.db.execute(
            select(Share).where(Share.share_code == share_code)
        )
        return result.scalar_one_or_none()
