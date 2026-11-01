"""用户业务服务"""

from app.db.models.user import User
from app.db.repositories.user_repo import UserRepository
from app.schemas.user import UserPreferences, UserProfile, UserProfileUpdateRequest


class UserService:
    """封装用户资料和偏好配置用例"""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_profile(self, user_id: str) -> UserProfile:
        """获取当前用户资料"""
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return UserProfile(id=user_id, nickname="旅行者")
        return self._to_profile(user)

    async def update_profile(
        self,
        user_id: str,
        request: UserProfileUpdateRequest,
    ) -> UserProfile:
        """更新当前用户资料"""
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return UserProfile(
                id=user_id,
                nickname=request.nickname or "旅行者",
                avatar_url=request.avatar_url,
            )

        if request.nickname is not None:
            user.username = request.nickname
        if request.avatar_url is not None:
            user.avatar = request.avatar_url
        await self.user_repository.update(user)
        return self._to_profile(user)

    async def get_preferences(self, user_id: str) -> UserPreferences:
        """获取偏好配置"""
        user = await self.user_repository.get_by_id(user_id)
        if user is None or not user.preferences:
            return UserPreferences()
        return UserPreferences(**user.preferences)

    async def update_preferences(
        self,
        user_id: str,
        preferences: UserPreferences,
    ) -> UserPreferences:
        """更新当前用户偏好配置"""
        user = await self.user_repository.get_by_id(user_id)
        if user is None:
            return preferences

        await self.user_repository.update_preferences(
            user=user,
            preferences=preferences.model_dump(),
        )
        return preferences

    def _to_profile(self, user: User) -> UserProfile:
        """转换 ORM 模型为用户资料响应"""
        return UserProfile(
            id=user.id,
            phone=None,
            nickname=user.username,
            avatar_url=user.avatar,
            created_at=user.created_at,
        )
