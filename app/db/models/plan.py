"""
旅行方案表
"""

from sqlalchemy import Column, String, Float, Date, Integer, JSON, DateTime, ForeignKey

from app.db.models.base import Base, UUIDMixin, TimestampMixin


class Plan(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "plans"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    destination = Column(String(100), nullable=False)
    departure = Column(String(100), nullable=True, doc="出发地")
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    budget = Column(Float, nullable=False)
    travelers = Column(Integer, default=1)
    crowd_type = Column(String(50), nullable=True, doc="人群类型: couple/family/solo/friends")
    travel_style = Column(String(50), nullable=True, doc="旅行风格: relaxed/balanced/intensive/food/culture/adventure")
    preferences = Column(JSON, default=list)
    status = Column(String(20), default="draft")  # draft / generating / completed / failed
    itinerary = Column(JSON, default=list)  # 行程详情（JSON）
    total_cost = Column(Float)
    saved_at = Column(DateTime, nullable=True, doc="用户主动保存时间，为空表示仅系统自动生成")
    is_favorite = Column(JSON, default=dict, doc="收藏状态")
    view_count = Column(Integer, default=0)
    version = Column(Integer, default=1)

    # 完整方案数据 JSON（final_plan 所有字段）
    full_data = Column(JSON, default=dict, doc="完整方案数据，含预算/交通/天气/美食等所有字段")

    # 各模块数据（冗余存储，方便按需读取，不增加额外 join）
    overview = Column(JSON, default=dict, doc="概览：highlights/total_distance/transport_modes")
    traffic_summary = Column(JSON, default=dict, doc="城际+城内交通汇总")
    food_summary = Column(JSON, default=dict, doc="美食推荐汇总")
    budget_detail = Column(JSON, default=dict, doc="预算明细 breakdown")
    souvenir_recommendations = Column(JSON, default=list, doc="纪念品推荐")
    weather_forecast = Column(JSON, default=list, doc="天气预报")
    packing_list = Column(JSON, default=list, doc="行李清单")
    tips = Column(JSON, default=list, doc="出行建议")
    avoid_list = Column(JSON, default=list, doc="避坑指南")
    hotel_plan = Column(JSON, default=dict, doc="住宿推荐及评分")
    big_traffic = Column(JSON, default=list, doc="大交通（火车/航班）")
    meal_plan = Column(JSON, default=list, doc="每日餐饮计划")
    attraction_details = Column(JSON, default=list, doc="景点深度详情")
    food_details = Column(JSON, default=list, doc="美食深度详情")
