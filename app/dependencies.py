"""
FastAPI 依赖注入 - 数据库会话、用户鉴权等
"""

import hashlib
from typing import AsyncGenerator

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.plan_repo import PlanRepository
from app.db.repositories.trip_repo import (
    TripRepository, CheckinRepository, ExpenseRepository, AdjustmentRepository,
)
from app.db.repositories.travelogue_repo import (
    TravelogueRepository, SocialMaterialRepository, ShareRepository,
)
from app.db.repositories.user_repo import UserRepository
from app.db.session import async_session_factory
from app.exceptions import UnauthorizedException
from app.services.application import (
    ConversationService,
    TravelPlanService,
    TravelogueService,
    TripService,
    UserService,
)


def anonymous_user_id(session_id: str) -> str:
    return f"anon:{hashlib.md5(session_id.encode()).hexdigest()[:31]}"


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话（依赖注入）"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_current_user(
    authorization: str = Header(None),
    x_session_id: str = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    JWT 鉴权依赖注入。

    优先级：
        1. Authorization: Bearer <JWT> → 解析 user_id
        2. X-Session-Id → 匿名会话
        3. 都没有 → 401
    """
    # 匿名会话
    if x_session_id and not authorization:
        user_id = anonymous_user_id(x_session_id)
        return {
            "user_id": user_id,
            "session_id": x_session_id,
            "anonymous": True,
        }

    if not authorization:
        raise UnauthorizedException("未登录，请先获取 Token")

    token = authorization.replace("Bearer ", "")

    try:
        from app.core.security import decode_access_token
        payload = decode_access_token(token)
    except Exception:
        raise UnauthorizedException("Token 无效或已过期，请重新登录")

    return {
        "user_id": payload["sub"],
        "token": token,
        "anonymous": False,
    }


async def get_user_service(
    db: AsyncSession = Depends(get_db),
) -> UserService:
    """获取用户业务服务"""
    return UserService(UserRepository(db))


async def get_plan_service(
    db: AsyncSession = Depends(get_db),
) -> TravelPlanService:
    """获取旅行方案业务服务"""
    return TravelPlanService(PlanRepository(db), UserRepository(db))


async def get_conversation_service() -> ConversationService:
    """获取对话业务服务"""
    return ConversationService()


async def get_trip_service(
    db: AsyncSession = Depends(get_db),
) -> TripService:
    """获取行程执行业务服务"""
    return TripService(
        TripRepository(db), CheckinRepository(db),
        ExpenseRepository(db), AdjustmentRepository(db),
        plan_repo=PlanRepository(db),
    )


async def get_travelogue_service(
    db: AsyncSession = Depends(get_db),
) -> TravelogueService:
    """获取游记业务服务"""
    return TravelogueService(
        TravelogueRepository(db),
        SocialMaterialRepository(db),
        ShareRepository(db),
    )
