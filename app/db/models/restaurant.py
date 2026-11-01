"""
餐厅基础表
"""

from sqlalchemy import Column, Float, JSON, String, UniqueConstraint

from app.db.models.base import Base, UUIDMixin, TimestampMixin


class Restaurant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "restaurants"
    __table_args__ = (
        UniqueConstraint("source", "source_poi_id", name="uq_restaurants_source_poi_id"),
    )

    name = Column(String(200), nullable=False)
    city = Column(String(50), nullable=False)
    source = Column(String(32), nullable=False, default="manual")
    source_poi_id = Column(String(128), nullable=True)
    cuisine = Column(String(50))  # 菜系（川菜、粤菜、日料等）
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(String(500))
    rating = Column(Float, default=0)
    avg_price = Column(Float, default=0)  # 人均价格
    opening_hours = Column(String(200))
    tags = Column(JSON, default=list)  # 标签（网红店、老字号、清真等）
    image_url = Column(String(500))
    description = Column(String(2000))
