"""用户 Repository"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户数据访问"""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def update_preferences(self, user: User, preferences: dict) -> User:
        """更新用户偏好配置"""
        user.preferences = preferences
        return await self.update(user)

    async def ensure_development_user(self, user_id: str) -> User:
        """
        确保开发态 mock 用户存在。

        当前鉴权仍返回固定 mock 用户；真实认证落地后应移除该兜底。
        """
        user = await self.get_by_id(user_id)
        if user is not None:
            return user

        return await self.create(
            User(
                id=user_id,
                username=user_id,
                hashed_password="mock-password",
                preferences={},
            )
        )
