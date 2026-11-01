"""
会话表 & 消息表 — 持久化对话历史

会话: 一次旅行规划对话
消息: 对话中的每条消息（用户/AI）
"""

from sqlalchemy import Boolean, Column, String, Text, Integer, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.models.base import Base, UUIDMixin, TimestampMixin


class Conversation(Base, UUIDMixin, TimestampMixin):
    """对话会话"""

    __tablename__ = "conversations"

    user_id = Column(String(36), nullable=True, doc="用户ID（匿名会话可为空）")
    title = Column(String(200), default="", doc="会话标题（自动生成）")
    status = Column(String(20), default="active", doc="active / completed / archived")
    destination = Column(String(100), doc="目的地")
    days = Column(Integer, doc="天数")
    plan_id = Column(String(36), nullable=True, doc="关联的旅行方案 ID")
    pinned = Column(Boolean, default=False, nullable=False, doc="是否置顶")

    messages = relationship("Message", back_populates="conversation",
                            order_by="Message.sequence", cascade="all, delete-orphan")
    plan_runs = relationship("ConversationPlanRun", back_populates="conversation",
                             order_by="ConversationPlanRun.sequence",
                             cascade="all, delete-orphan")


class Message(Base, UUIDMixin, TimestampMixin):
    """单条消息"""

    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "sequence", name="uq_messages_conversation_sequence"),
        UniqueConstraint("conversation_id", "client_message_id", name="uq_messages_conversation_client_message"),
    )

    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    role = Column(String(20), nullable=False, doc="user / assistant / system")
    content = Column(Text, nullable=False)
    sequence = Column(Integer, default=0, nullable=False, doc="消息序号（递增）")
    message_type = Column(String(30), default="text", nullable=False,
                          doc="text / plan_result / plan_progress")
    metadata_json = Column(JSON, default=dict, nullable=False, doc="消息附加元数据")
    client_message_id = Column(String(64), nullable=True, doc="客户端消息幂等 ID")

    conversation = relationship("Conversation", back_populates="messages")


class ConversationPlanRun(Base, UUIDMixin, TimestampMixin):
    """一次会话中的一份生成方案。"""

    __tablename__ = "conversation_plan_runs"
    __table_args__ = (
        UniqueConstraint(
            "conversation_id", "sequence",
            name="uq_conversation_plan_runs_conversation_sequence",
        ),
    )

    conversation_id = Column(String(36), ForeignKey("conversations.id"), nullable=False)
    sequence = Column(Integer, default=0, nullable=False, doc="会话内方案序号")
    destination = Column(String(100), default="", doc="目的地")
    days = Column(Integer, default=0, doc="天数")
    summary = Column(JSON, default=dict, doc="方案摘要 JSON")

    conversation = relationship("Conversation", back_populates="plan_runs")
