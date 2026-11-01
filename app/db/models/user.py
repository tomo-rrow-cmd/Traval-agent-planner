"""
用户表
"""

from sqlalchemy import Column, String, JSON

from app.db.models.base import Base, UUIDMixin, TimestampMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    phone = Column(String(20), unique=True, nullable=True, index=True)
    username = Column(String(50), unique=True, nullable=True)
    email = Column(String(100), unique=True, nullable=True)
    hashed_password = Column(String(255), nullable=False)
    nickname = Column(String(50), default="旅行者")
    avatar = Column(String(500))
    preferences = Column(JSON, default=dict)
