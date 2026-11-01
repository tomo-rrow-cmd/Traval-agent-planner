"""
基础模型类 - 所有 ORM 模型的抽象基类

    参考：.agent/conventions.md §5
    业务表默认包含 id / created_at / updated_at；
    需要删除恢复能力时显式继承软删除混入。
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String
from sqlalchemy.orm import declarative_base


def generate_uuid() -> str:
    """生成 UUID 主键"""
    return str(uuid.uuid4())


Base = declarative_base()


class TimestampMixin:
    """创建时间 & 更新时间混入"""

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
        doc="创建时间",
    )
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
        doc="最近更新时间",
    )


class SoftDeleteMixin:
    """
    软删除混入。

    需要删除恢复能力的表显式继承此类。
    查询时是否过滤 deleted_at 由具体 Repository / Service 决定。
    参考：.agent/conventions.md §5
    """

    deleted_at = Column(
        DateTime,
        default=None,
        nullable=True,
        doc="软删除时间，非 NULL 表示已删除",
    )
    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        doc="是否已删除（冗余字段，便于索引和查询）",
    )

    def soft_delete(self) -> None:
        """标记为已删除"""
        self.deleted_at = datetime.utcnow()
        self.is_deleted = True


class UUIDMixin:
    """UUID 主键混入"""

    id = Column(String(36), primary_key=True, default=generate_uuid)
