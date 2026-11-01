"""用户接口 - 对齐 docs/api/API接口规范文档.md §3"""

from fastapi import APIRouter, Depends

from app.dependencies import (
    anonymous_user_id,
    get_conversation_service,
    get_current_user,
    get_user_service,
)
from app.exceptions import UnauthorizedException
from app.schemas.common import BaseResponse
from app.schemas.user import (
    AnonymousMergeRequest,
    AnonymousMergeResult,
    UserPreferences,
    UserProfile,
    UserProfileUpdateRequest,
)
from app.services.application import ConversationService, UserService

router = APIRouter(prefix="/user", tags=["用户接口"])


@router.get("/profile", response_model=BaseResponse[UserProfile])
async def get_profile(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """获取用户资料"""
    return BaseResponse(
        data=await user_service.get_profile(current_user["user_id"])
    )


@router.put("/profile", response_model=BaseResponse[UserProfile])
async def update_profile(
    request: UserProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """更新用户资料"""
    return BaseResponse(
        data=await user_service.update_profile(
            user_id=current_user["user_id"],
            request=request,
        )
    )


@router.get("/preferences", response_model=BaseResponse[UserPreferences])
async def get_preferences(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """获取偏好配置"""
    return BaseResponse(
        data=await user_service.get_preferences(current_user["user_id"])
    )


@router.put("/preferences", response_model=BaseResponse[UserPreferences])
async def update_preferences(
    preferences: UserPreferences,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service),
):
    """更新偏好配置"""
    return BaseResponse(
        data=await user_service.update_preferences(
            user_id=current_user["user_id"],
            preferences=preferences,
        )
    )


@router.post("/sessions/anonymous/merge", response_model=BaseResponse[AnonymousMergeResult])
async def merge_anonymous_session(
    request: AnonymousMergeRequest,
    current_user: dict = Depends(get_current_user),
    conversation_service: ConversationService = Depends(get_conversation_service),
):
    if current_user.get("anonymous"):
        raise UnauthorizedException("请登录后再合并匿名会话")
    merged_count = await conversation_service.merge_sessions(
        anonymous_user_id(request.anonymous_session_id),
        current_user["user_id"],
    )
    return BaseResponse(data=AnonymousMergeResult(
        merged_session_count=merged_count,
        merged_plan_count=0,
    ))
