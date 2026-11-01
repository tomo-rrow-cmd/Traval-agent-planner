"""
认证接口 — JWT 鉴权

POST /auth/register     → 手机号+密码注册
POST /auth/sms-codes    → 发送短信验证码（mock）
POST /auth/sessions     → 手机验证码/密码登录 → JWT
POST /auth/tokens       → 刷新 Token
DELETE /auth/sessions/current → 登出
"""

from fastapi import APIRouter, Depends

from app.db.session import async_session_factory
from app.db.models.user import User
from app.core.security import (
    create_access_token, create_refresh_token,
    decode_refresh_token, hash_password, verify_password,
)
from app.dependencies import get_current_user
from app.schemas.common import BaseResponse, EmptyData
from app.schemas.user import (
    LoginRequest, RefreshTokenRequest, RegisterRequest,
    SmsCodeRequest, SmsCodeResult, TokenResult, UserProfile,
)
from sqlalchemy import select

router = APIRouter(prefix="/auth", tags=["认证接口"])


@router.post("/register", response_model=BaseResponse[TokenResult])
async def register(request: RegisterRequest):
    """手机号+密码注册"""
    async with async_session_factory() as db:
        # 检查手机号是否已注册
        existing = (await db.execute(
            select(User).where(User.phone == request.phone)
        )).scalar_one_or_none()

        if existing:
            return BaseResponse(code=10002, message="手机号已注册")

        user = User(
            phone=request.phone,
            hashed_password=hash_password(request.password),
            nickname=request.nickname or f"旅行者{request.phone[-4:]}",
        )
        db.add(user)
        await db.commit()

        access = create_access_token(user.id, {"phone": user.phone})
        refresh = create_refresh_token(user.id)

        return BaseResponse(data=TokenResult(
            access_token=access,
            refresh_token=refresh,
            expires_in=7200,
            user=UserProfile(
                id=user.id,
                phone=f"{user.phone[:3]}****{user.phone[-4:]}",
                nickname=user.nickname,
            ),
        ))


@router.post("/sms-codes", response_model=BaseResponse[SmsCodeResult])
async def send_sms_code(request: SmsCodeRequest):
    """发送短信验证码（mock — 开发环境任意手机号，验证码固定 123456）"""
    _ = request
    return BaseResponse(data=SmsCodeResult())


@router.post("/sessions", response_model=BaseResponse[TokenResult])
async def create_session(request: LoginRequest):
    """登录 — 支持验证码和密码两种方式"""
    async with async_session_factory() as db:
        user = (await db.execute(
            select(User).where(User.phone == request.phone)
        )).scalar_one_or_none()

        # 验证码登录
        if request.method == "phone":
            if request.code != "123456":  # 开发环境固定验证码
                return BaseResponse(code=20001, message="验证码错误")
            # 用户不存在自动注册
            if not user:
                user = User(
                    phone=request.phone,
                    hashed_password=hash_password("default"),
                    nickname=f"旅行者{request.phone[-4:]}",
                )
                db.add(user)
                await db.commit()

        # 密码登录
        elif request.method == "password":
            if not user:
                return BaseResponse(code=20001, message="手机号未注册")
            if not verify_password(request.password or "", user.hashed_password):
                return BaseResponse(code=20001, message="密码错误")
        else:
            return BaseResponse(code=10001, message="不支持登录方式")

        access = create_access_token(user.id, {"phone": user.phone})
        refresh = create_refresh_token(user.id)

        return BaseResponse(data=TokenResult(
            access_token=access,
            refresh_token=refresh,
            expires_in=7200,
            user=UserProfile(
                id=user.id,
                phone=f"{user.phone[:3]}****{user.phone[-4:]}",
                nickname=user.nickname or "旅行者",
            ),
        ))


@router.post("/tokens", response_model=BaseResponse[TokenResult])
async def refresh_token(request: RefreshTokenRequest):
    """刷新 Token"""
    try:
        payload = decode_refresh_token(request.refresh_token)
    except Exception:
        return BaseResponse(code=20001, message="Refresh Token 无效或已过期")

    user_id = payload["sub"]

    async with async_session_factory() as db:
        user = (await db.execute(
            select(User).where(User.id == user_id)
        )).scalar_one_or_none()

        if not user:
            return BaseResponse(code=20001, message="用户不存在")

        access = create_access_token(user.id, {"phone": user.phone})
        refresh = create_refresh_token(user.id)

        return BaseResponse(data=TokenResult(
            access_token=access,
            refresh_token=refresh,
            expires_in=7200,
        ))


@router.delete("/sessions/current", response_model=BaseResponse[EmptyData])
async def logout(current_user: dict = Depends(get_current_user)):
    """登出（客户端删除 Token 即可，服务端无状态）"""
    _ = current_user
    return BaseResponse(data=EmptyData())
