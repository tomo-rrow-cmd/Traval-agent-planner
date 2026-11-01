from __future__ import annotations

"""
通用响应结构

符合 .agent/conventions.md §4 的统一响应格式：
    {"code": 0, "message": "ok", "data": {}, "request_id": "req_xxx"}
"""

import math
import uuid
from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


def _generate_request_id() -> str:
    """生成请求追踪 ID"""
    return f"req_{uuid.uuid4().hex[:12]}"


class BaseResponse(BaseModel, Generic[T]):
    """通用成功响应包装"""

    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="ok", description="状态描述")
    data: Optional[T] = Field(default=None, description="响应数据")
    request_id: str = Field(default_factory=_generate_request_id, description="请求追踪 ID")


class PaginatedData(BaseModel, Generic[T]):
    """分页数据结构"""

    list: List[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总记录数")
    page: int = Field(default=1, ge=1, description="当前页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=200, description="每页条数")
    total_pages: int = Field(default=0, description="总页数")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedData[T]":
        """按文档分页字段创建响应数据"""
        total_pages = math.ceil(total / page_size) if page_size else 0
        return cls(
            list=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class CursorPaginatedData(BaseModel, Generic[T]):
    """游标分页数据结构"""

    list: List[T] = Field(default_factory=list, description="数据列表")
    has_more: bool = Field(default=False, description="是否还有更多数据")
    next_before_id: Optional[str] = Field(default=None, description="下一页 before_id")
    next_after_id: Optional[str] = Field(default=None, description="下一页 after_id")


class ErrorResponse(BaseModel):
    """错误响应——不得暴露堆栈、SQL、密钥等内部细节"""

    code: int = Field(..., description="错误码")
    message: str = Field(..., description="用户可读的错误描述")
    data: None = Field(default=None, description="失败响应数据固定为 null")
    request_id: str = Field(default_factory=_generate_request_id, description="请求追踪 ID")


class EmptyData(BaseModel):
    """空对象响应"""


class TaskStatus(BaseModel):
    """异步任务状态"""

    task_id: str
    type: str = "plan_export"
    status: str = "processing"
    progress: int = 0
    message: Optional[str] = None
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None
    error: Optional[dict] = None


class HealthData(BaseModel):
    """健康检查数据"""

    status: str = "healthy"
    version: str = "1.0.0"
    uptime_seconds: int = 0
    dependencies: dict[str, str] = Field(default_factory=dict)
