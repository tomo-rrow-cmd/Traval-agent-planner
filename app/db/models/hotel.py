"""
酒店基础表
"""

from sqlalchemy import Column, Float, Integer, JSON, String, UniqueConstraint

from app.db.models.base import Base, UUIDMixin, TimestampMixin


class Hotel(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "hotels"
    __table_args__ = (
        UniqueConstraint("source", "source_poi_id", name="uq_hotels_source_poi_id"),
    )

    name = Column(String(200), nullable=False)
    city = Column(String(50), nullable=False)
    source = Column(String(32), nullable=False, default="manual")
    source_poi_id = Column(String(128), nullable=True)
    star = Column(Integer, default=3)  # 星级
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(String(500))
    rating = Column(Float, default=0)
    price_per_night = Column(Float, default=0)  # 每晚价格
    amenities = Column(JSON, default=list)  # 设施（WiFi、停车、早餐等）
    image_url = Column(String(500))
    description = Column(String(2000))
