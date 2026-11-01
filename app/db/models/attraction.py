"""
景点基础表
"""

from sqlalchemy import Column, Float, JSON, String, UniqueConstraint

from app.db.models.base import Base, UUIDMixin, TimestampMixin


class Attraction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "attractions"
    __table_args__ = (
        UniqueConstraint("source", "source_poi_id", name="uq_attractions_source_poi_id"),
    )

    name = Column(String(200), nullable=False)
    city = Column(String(50), nullable=False)
    source = Column(String(32), nullable=False, default="manual")
    source_poi_id = Column(String(128), nullable=True)
    category = Column(String(50))  # 自然风光 / 历史人文 / 主题公园 / 购物等
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(String(500))
    rating = Column(Float, default=0)
    price = Column(Float, default=0)  # 门票价格
    opening_hours = Column(String(200))
    recommended_duration = Column(Float)  # 建议游览时长（小时）
    tags = Column(JSON, default=list)  # 标签列表
    image_url = Column(String(500))
    description = Column(String(2000))
