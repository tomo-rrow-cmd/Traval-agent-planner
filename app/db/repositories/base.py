"""
Repository 层 — 统一数据访问抽象

所有数据库查询必须通过 Repository 或 Service 层，
API 层和 Agent 层禁止直接操作 ORM Session。

参考：.agent/architecture.md §3, .agent/conventions.md §2
"""

from typing import Any, Generic, Optional, Sequence, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """
    通用 Repository 基类。

    提供标准 CRUD 操作，子类按需覆盖或扩展。
    """

    def __init__(self, model: type[ModelT], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, entity_id: str) -> Optional[ModelT]:
        """按主键查询"""
        result = await self.db.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        offset: int = 0,
        limit: int = 100,
    ) -> Sequence[ModelT]:
        """分页查询全部"""
        result = await self.db.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def count(self, **filters: Any) -> int:
        """计数"""
        query = select(func.count()).select_from(self.model)
        for attr, value in filters.items():
            if value is not None:
                query = query.where(getattr(self.model, attr) == value)
        result = await self.db.execute(query)
        return result.scalar_one()

    async def create(self, entity: ModelT) -> ModelT:
        """新增"""
        self.db.add(entity)
        await self.db.flush()
        return entity

    async def update(self, entity: ModelT) -> ModelT:
        """更新"""
        await self.db.flush()
        return entity

    async def delete(self, entity: ModelT, soft: bool = False) -> None:
        """
        删除（默认物理删除）。

        参考：.agent/conventions.md §5
        """
        if soft and hasattr(entity, "deleted_at"):
            from datetime import datetime

            entity.deleted_at = datetime.utcnow()  # type: ignore[attr-defined]
            await self.db.flush()
        else:
            await self.db.delete(entity)
            await self.db.flush()
