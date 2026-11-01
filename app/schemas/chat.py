"""
对话相关数据结构
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, model_validator


class ChatSessionCreateRequest(BaseModel):
    """创建会话请求"""

    title: Optional[str] = Field(default=None, max_length=100, description="会话标题")


class ChatSessionUpdateRequest(BaseModel):
    """更新会话标题或置顶状态。"""

    title: Optional[str] = Field(default=None, min_length=1, max_length=100)
    pinned: Optional[bool] = None

    @model_validator(mode="after")
    def validate_update(self):
        if self.title is None and self.pinned is None:
            raise ValueError("at least one field is required")
        if self.title is not None:
            self.title = self.title.strip()
            if not self.title:
                raise ValueError("title must not be blank")
        return self


class ChatSession(BaseModel):
    """会话响应"""

    id: str
    title: str
    status: str = "active"
    message_count: int = 0
    pinned: bool = False
    plan_run_id: Optional[str] = None
    last_message_preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChatMessageCreateRequest(BaseModel):
    """发送消息请求"""

    content: str = Field(default="", max_length=2000, description="用户消息（图片可无文字）")
    images: list[str] = Field(default_factory=list, max_length=9, description="图片 URL 列表")
    client_message_id: Optional[str] = Field(default=None, min_length=1, max_length=64)

    @model_validator(mode="after")
    def validate_content_or_images(self):
        if not self.content and not self.images:
            raise ValueError("content and images cannot both be empty")
        return self


class MessageRecord(BaseModel):
    """单条消息记录"""

    id: str
    session_id: str
    role: str
    content: str
    message_type: str = "text"
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConversationPlanRunRecord(BaseModel):
    """同一会话中的一次方案生成结果。"""

    id: str
    destination: str
    days: int = 0
    summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class StreamEvent(BaseModel):
    """SSE 事件载荷"""

    event: str
    data: dict[str, Any]
