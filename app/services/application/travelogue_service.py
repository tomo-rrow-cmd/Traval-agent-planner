"""游记 & 社交素材 & 分享业务服务"""

from app.db.repositories.travelogue_repo import (
    TravelogueRepository, SocialMaterialRepository, ShareRepository,
)
from app.schemas.common import PaginatedData


class TravelogueService:
    """游记核心业务逻辑"""

    def __init__(self, travelogue_repo: TravelogueRepository,
                 material_repo: SocialMaterialRepository,
                 share_repo: ShareRepository):
        self.travelogue_repo = travelogue_repo
        self.material_repo = material_repo
        self.share_repo = share_repo

    # ---- Travelogues ----

    async def create(self, trip_id: str, user_id: str, **kwargs) -> dict:
        t = await self.travelogue_repo.create_for_trip(trip_id, user_id, **kwargs)
        return self._tr_to_dict(t)

    async def get(self, travelogue_id: str) -> dict | None:
        t = await self.travelogue_repo.get_by_id(travelogue_id)
        return self._tr_to_dict(t) if t else None

    async def get_by_trip(self, trip_id: str) -> dict | None:
        t = await self.travelogue_repo.get_by_trip(trip_id)
        return self._tr_to_dict(t) if t else None

    async def list_by_user(self, user_id: str, status: str | None = None,
                           page: int = 1, page_size: int = 20) -> PaginatedData:
        offset = (page - 1) * page_size
        items = await self.travelogue_repo.list_by_user(user_id, status, offset, page_size)
        total = await self.travelogue_repo.count_by_user(user_id)
        return PaginatedData.create(
            [self._tr_to_dict(t) for t in items],
            total=total, page=page, page_size=page_size,
        )

    async def update(self, travelogue_id: str, user_id: str | None = None, **kwargs) -> dict:
        t = await self.travelogue_repo.get_by_id(travelogue_id)
        if not t:
            raise ValueError("Travelogue not found")
        if user_id and t.user_id != user_id:
            raise PermissionError("Permission denied")
        for k, v in kwargs.items():
            if hasattr(t, k) and v is not None:
                setattr(t, k, v)
        await self.travelogue_repo.update(t)
        return self._tr_to_dict(t)

    async def publish(self, travelogue_id: str, user_id: str | None = None) -> dict:
        return await self.update(travelogue_id, user_id=user_id, status="published")

    async def delete(self, travelogue_id: str) -> bool:
        return await self.travelogue_repo.delete_by_id(travelogue_id)

    async def delete_by_user(self, travelogue_id: str, user_id: str) -> bool:
        t = await self.travelogue_repo.get_by_id(travelogue_id)
        if not t:
            raise ValueError("Travelogue not found")
        if t.user_id != user_id:
            raise PermissionError("Permission denied")
        return await self.travelogue_repo.delete_by_id(travelogue_id)

    # ---- Social Materials ----

    async def create_material(self, trip_id: str, user_id: str, **kwargs) -> dict:
        m = await self.material_repo.create_material(trip_id, user_id, **kwargs)
        return self._mat_to_dict(m)

    async def list_materials(self, trip_id: str, type: str | None = None) -> list[dict]:
        items = await self.material_repo.list_by_trip(trip_id, type)
        return [self._mat_to_dict(m) for m in items]

    async def favorite_material(self, material_id: str, is_favorite: bool = True) -> dict:
        m = await self.material_repo.get_by_id(material_id)
        if not m:
            raise ValueError("Material not found")
        m.is_favorite = is_favorite
        await self.material_repo.update(m)
        return self._mat_to_dict(m)

    async def mark_used_in_travelogue(self, material_id: str) -> dict:
        m = await self.material_repo.get_by_id(material_id)
        if not m:
            raise ValueError("Material not found")
        m.used_in_travelogue = True
        await self.material_repo.update(m)
        return self._mat_to_dict(m)

    # ---- Shares ----

    async def create_share(self, user_id: str, target_type: str, target_id: str,
                           share_code: str, password: str | None = None, expire_at=None) -> dict:
        s = await self.share_repo.create_share(
            user_id, target_type, target_id, share_code, password, expire_at)
        return self._share_to_dict(s)

    async def get_share_by_code(self, share_code: str) -> dict | None:
        s = await self.share_repo.get_by_code(share_code)
        return self._share_to_dict(s) if s else None

    async def increment_view(self, share_code: str) -> None:
        s = await self.share_repo.get_by_code(share_code)
        if s:
            s.view_count = (s.view_count or 0) + 1
            await self.share_repo.update(s)

    async def get_share_password(self, share_code: str) -> str | None:
        """获取分享密码（用于校验）"""
        s = await self.share_repo.get_by_code(share_code)
        return s.password if s else None

    # ---- Serializers ----

    def _tr_to_dict(self, t) -> dict:
        return {
            "id": t.id, "trip_id": t.trip_id, "user_id": t.user_id,
            "title": t.title, "content": t.content, "cover_url": t.cover_url,
            "style": t.style or "diary",
            "photos": t.photos or [],
            "total_days": t.total_days, "total_pois": t.total_pois,
            "total_cost": t.total_cost, "total_photos": t.total_photos,
            "status": t.status,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }

    def _mat_to_dict(self, m) -> dict:
        return {
            "id": m.id, "trip_id": m.trip_id, "user_id": m.user_id,
            "type": m.type, "title": m.title, "content": m.content,
            "hashtags": m.hashtags or [], "location_tag": m.location_tag,
            "images": m.images or [], "layout": m.layout,
            "overlay_data": m.overlay_data,
            "source_day": m.source_day, "source_poi": m.source_poi,
            "is_generated": m.is_generated, "is_favorite": m.is_favorite,
            "used_in_travelogue": m.used_in_travelogue,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }

    def _share_to_dict(self, s) -> dict:
        return {
            "id": s.id, "user_id": s.user_id,
            "target_type": s.target_type, "target_id": s.target_id,
            "share_code": s.share_code,
            "has_password": s.password is not None,
            "expire_at": s.expire_at.isoformat() if s.expire_at else None,
            "view_count": s.view_count,
            "share_url": f"https://travel.example.com/s/{s.share_code}",
        }
