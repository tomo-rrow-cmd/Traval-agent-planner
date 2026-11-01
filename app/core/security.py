"""
JWT 鉴权 + 密码哈希

Access Token:  短有效期 (默认 2 小时)，用于 API 鉴权
Refresh Token: 长有效期 (默认 7 天)，用于刷新 Access Token
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from app.config import settings

# ---- JWT ----

ALGORITHM = "HS256"


def create_access_token(user_id: str, extra: Optional[dict] = None) -> str:
    """生成 Access Token"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=settings.JWT_ACCESS_EXPIRE),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """生成 Refresh Token"""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(seconds=settings.JWT_REFRESH_EXPIRE),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    解码并验证 JWT Token。
    返回 payload，Token 无效/过期时抛出异常。
    """
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])


def decode_access_token(token: str) -> dict:
    """解码 Access Token，非 access 类型抛异常"""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("Token 类型错误")
    return payload


def decode_refresh_token(token: str) -> dict:
    """解码 Refresh Token"""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise jwt.InvalidTokenError("Token 类型错误")
    return payload


# ---- 密码 ----

def hash_password(password: str) -> str:
    """bcrypt 哈希密码"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    """验证密码"""
    return bcrypt.checkpw(password.encode(), hashed.encode())
