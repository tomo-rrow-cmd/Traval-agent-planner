"""
用户配置数据结构
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """用户个人信息"""

    id: str
    phone: Optional[str] = None
    nickname: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: Optional[datetime] = None


class UserProfileUpdateRequest(BaseModel):
    """更新用户资料请求"""

    nickname: Optional[str] = Field(default=None, max_length=50)
    avatar_url: Optional[str] = Field(default=None, max_length=500)


class UserPreferences(BaseModel):
    """用户旅行偏好"""

    travel_style: Optional[str] = "balanced"
    budget_level: Optional[str] = "cost_effective"
    pace: Optional[str] = "moderate"
    diet_preferences: list[str] = Field(default_factory=list)
    food_taboos: list[str] = Field(default_factory=list)
    accommodation: Optional[str] = "business"
    transport: Optional[str] = "time_first"
    start_time: Optional[str] = "09:00"
    end_time: Optional[str] = "21:00"
    need_nap: bool = False
    avoid_tags: list[str] = Field(default_factory=list)
    must_visit_places: list[str] = Field(default_factory=list)
    special_requests: str = ""
    custom_agent_name: str = "小旅"
    agent_personality: str = "friendly"


class AnonymousMergeRequest(BaseModel):
    """匿名会话合并请求"""

    anonymous_session_id: str


class AnonymousMergeResult(BaseModel):
    """匿名会话合并结果"""

    merged_session_count: int = 0
    merged_plan_count: int = 0


class SmsCodeRequest(BaseModel):
    """短信验证码请求"""

    phone: str = Field(..., min_length=11, max_length=11)


class SmsCodeResult(BaseModel):
    """短信验证码发送结果"""

    expires_in: int = 60
    retry_after: int = 60
    need_captcha: bool = False


class RegisterRequest(BaseModel):
    """注册请求"""

    phone: str = Field(..., min_length=11, max_length=11)
    password: str = Field(..., min_length=6, max_length=64)
    nickname: Optional[str] = Field(None, max_length=32)


class LoginRequest(BaseModel):
    """登录请求 — method: phone(验证码) / password(密码)"""

    method: str = "phone"
    phone: str = Field(..., min_length=11, max_length=11)
    code: Optional[str] = Field(None, min_length=4, max_length=8)
    password: Optional[str] = Field(None, min_length=6, max_length=64)


class RefreshTokenRequest(BaseModel):
    """刷新 Token 请求"""

    refresh_token: str


class TokenResult(BaseModel):
    """Token 响应"""

    access_token: str
    refresh_token: str
    expires_in: int = 7200
    user: Optional[UserProfile] = None
