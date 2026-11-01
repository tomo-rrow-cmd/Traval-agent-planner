"""
V2.0 行程执行相关表 — trip_states / checkins / expense_records / adjustments

行程状态机: active → paused → active → completed/abandoned
"""

from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.db.models.base import Base, UUIDMixin, TimestampMixin


class TripState(Base, UUIDMixin, TimestampMixin):
    """行程执行状态 — 从方案创建，追踪旅行中的进度/位置/预算"""

    __tablename__ = "trip_states"

    plan_id = Column(String(36), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, doc="关联方案")
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, doc="用户")

    # 状态机: active / paused / completed / abandoned
    status = Column(String(20), default="active", nullable=False)

    # 进度追踪
    current_day = Column(Integer, default=1, doc="当前第几天")
    total_pois = Column(Integer, default=0, doc="总打卡目标数")
    checked_in = Column(Integer, default=0, doc="已打卡数")

    # 时间节点
    started_at = Column(DateTime, nullable=True, doc="开始旅行时间")
    paused_at = Column(DateTime, nullable=True, doc="暂停时间")
    completed_at = Column(DateTime, nullable=True, doc="完成时间")

    # 实时位置（最后一次签到位置）
    last_lat = Column(Float, nullable=True)
    last_lng = Column(Float, nullable=True)

    # 动态预算
    budget_total = Column(Float, nullable=True, doc="原始总预算")
    budget_spent = Column(Float, default=0.0, doc="已花费")
    budget_remain = Column(Float, nullable=True, doc="剩余预算")

    # 关联
    checkins = relationship("Checkin", back_populates="trip", order_by="Checkin.actual_at",
                            cascade="all, delete-orphan")
    expenses = relationship("ExpenseRecord", back_populates="trip",
                            cascade="all, delete-orphan")
    adjustments = relationship("Adjustment", back_populates="trip",
                               order_by="Adjustment.created_at", cascade="all, delete-orphan")


class Checkin(Base, UUIDMixin, TimestampMixin):
    """签到记录 — 到达景点/餐厅/酒店时打卡"""

    __tablename__ = "checkins"

    trip_id = Column(String(36), ForeignKey("trip_states.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # 签到目标
    poi_type = Column(String(20), nullable=False, doc="attraction / restaurant / hotel / other")
    poi_name = Column(String(200), nullable=False)
    poi_id = Column(String(36), nullable=True, doc="对应 attractions/restaurants/hotels 表的 ID")

    # 位置
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)

    # 照片 — JSONB: [{"url":"...", "thumbnail_url":"...", "ai_caption":"...", "ai_tags":[...], "quality_score":0.9}]
    photos = Column(JSON, default=list)

    # 来源天数（从方案 daily_itinerary 提取，供按天过滤和游记分组）
    source_day = Column(Integer, nullable=True, doc="签到所属第几天")

    # 时间对比
    planned_at = Column(String(10), nullable=True, doc="计划时间 HH:MM")
    actual_at = Column(DateTime, nullable=True, doc="实际签到时间")
    time_delta_min = Column(Integer, default=0, doc="偏差分钟数，正=迟到")

    # 花费
    planned_cost = Column(Float, nullable=True)
    actual_cost = Column(Float, nullable=True)

    # 感受（供游记用）
    rating = Column(Integer, nullable=True, doc="1-5 评分")
    note = Column(Text, nullable=True, doc="用户备注")

    trip = relationship("TripState", back_populates="checkins")


class ExpenseRecord(Base, UUIDMixin, TimestampMixin):
    """实际花费记录"""

    __tablename__ = "expense_records"

    trip_id = Column(String(36), ForeignKey("trip_states.id", ondelete="CASCADE"), nullable=False)
    checkin_id = Column(String(36), ForeignKey("checkins.id"), nullable=True, doc="关联签到，可为空")

    category = Column(String(20), nullable=False, doc="住宿/交通/餐饮/门票/购物/其他")
    amount = Column(Float, nullable=False)
    planned_amount = Column(Float, nullable=True, doc="原计划金额")
    note = Column(Text, nullable=True)

    spent_at = Column(DateTime, nullable=True, doc="消费时间")

    trip = relationship("TripState", back_populates="expenses")


class Adjustment(Base, UUIDMixin, TimestampMixin):
    """行程调整记录 — 天气/时间/预算触发"""

    __tablename__ = "adjustments"

    trip_id = Column(String(36), ForeignKey("trip_states.id", ondelete="CASCADE"), nullable=False)

    # 触发原因
    trigger_type = Column(String(30), nullable=False, doc="weather / time_drift / user_request / budget_alert")
    trigger_detail = Column(JSON, nullable=True, doc='{"weather":"暴雨","affected_days":[2,3]}')

    # 变更内容
    original_plan = Column(JSON, nullable=True, doc="原始受影响行程")
    adjusted_plan = Column(JSON, nullable=True, doc="调整后行程")
    reason = Column(Text, nullable=True, doc="调整说明")

    # 状态: pending / accepted / rejected / applied
    status = Column(String(20), default="pending", nullable=False)
    accepted_at = Column(DateTime, nullable=True)

    trip = relationship("TripState", back_populates="adjustments")
