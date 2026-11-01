"""行程执行相关 Pydantic Schemas"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ========== Trip ==========

class TripStartRequest(BaseModel):
    plan_id: str = Field(..., description="关联方案 ID")

class TripStatusUpdateRequest(BaseModel):
    status: str = Field(..., description="目标状态: paused / active / completed / abandoned")

class TripResponse(BaseModel):
    id: str
    plan_id: str
    user_id: str
    status: str
    current_day: int = 1
    total_pois: int = 0
    checked_in: int = 0
    started_at: str | None = None
    paused_at: str | None = None
    completed_at: str | None = None
    last_lat: float | None = None
    last_lng: float | None = None
    budget_total: float | None = None
    budget_spent: float = 0
    budget_remain: float | None = None
    created_at: str | None = None
    updated_at: str | None = None

class TripProgressResponse(BaseModel):
    trip_id: str
    status: str
    current_day: int = 1
    progress_pct: float = 0
    checked_in: int = 0
    total_pois: int = 0
    budget_total: float = 0
    budget_spent: float = 0
    budget_remain: float = 0
    time_delta_total_min: int = 0
    last_location: dict | None = None


# ========== Checkin ==========

class CheckinCreateRequest(BaseModel):
    poi_type: str = Field(..., description="attraction / restaurant / hotel / other")
    poi_name: str = Field(..., min_length=1, max_length=200)
    poi_id: str | None = None
    source_day: int | None = Field(None, description="签到所属第几天")
    lat: float | None = None
    lng: float | None = None
    photos: list[dict] = []
    planned_at: str | None = None
    actual_at: str | None = None
    planned_cost: float | None = None
    actual_cost: float | None = None
    rating: int | None = Field(None, ge=1, le=5)
    note: str | None = None

    @field_validator("actual_at", mode="before")
    @classmethod
    def coerce_actual_at(cls, v):
        """接受 datetime 或 ISO 字符串，统一输出 ISO 字符串"""
        if isinstance(v, datetime):
            return v.isoformat()
        return v

class CheckinResponse(BaseModel):
    id: str
    trip_id: str
    poi_type: str
    poi_name: str
    poi_id: str | None = None
    source_day: int | None = None
    lat: float | None = None
    lng: float | None = None
    photos: list[dict] = []
    planned_at: str | None = None
    actual_at: str | None = None
    time_delta_min: int = 0
    planned_cost: float | None = None
    actual_cost: float | None = None
    rating: int | None = None
    note: str | None = None
    created_at: str | None = None


# ========== Expense ==========

class ExpenseCreateRequest(BaseModel):
    category: str = Field(..., description="住宿/交通/餐饮/门票/购物/其他")
    amount: float = Field(..., gt=0)
    planned_amount: float | None = None
    note: str | None = None
    spent_at: str | None = None
    checkin_id: str | None = None

class ExpenseResponse(BaseModel):
    id: str
    trip_id: str
    checkin_id: str | None = None
    category: str
    amount: float
    planned_amount: float | None = None
    note: str | None = None
    spent_at: str | None = None


# ========== Adjustment ==========

class AdjustmentCreateRequest(BaseModel):
    trigger_type: str = Field(..., description="weather / time_drift / user_request / budget_alert")
    trigger_detail: dict | None = None
    daily_plan: list[dict] = []
    preferences: list[str] = []
    destination: str = ""

class AdjustmentResponse(BaseModel):
    id: str
    trip_id: str
    trigger_type: str
    trigger_detail: dict | None = None
    original_plan: list[dict] | None = None
    adjusted_plan: list[dict] | None = None
    reason: str | None = None
    status: str = "pending"
    accepted_at: str | None = None
    created_at: str | None = None


# ========== Reminder ==========

class ReminderRequest(BaseModel):
    tomorrow_day: int = 1
    destination: str = ""

class ReminderResponse(BaseModel):
    day: int
    reminder_text: str
    first_stop: str = ""
    first_stop_time: str = "08:00"
    weather_advice: str = ""
    packing_hint: str = ""


# ========== Annotate Photos ==========

class PhotoAnnotateRequest(BaseModel):
    checkin: dict = Field(..., description="签到数据含 photos 字段")


# ========== Share ==========

class ShareCreateRequest(BaseModel):
    target_type: str = Field(..., description="plan / travelogue")
    target_id: str = Field(...)
    password: str | None = None
    expire_hours: int | None = None  # 过期小时数

class ShareResponse(BaseModel):
    id: str
    user_id: str
    target_type: str
    target_id: str
    share_code: str
    has_password: bool = False
    expire_at: str | None = None
    view_count: int = 0
    share_url: str = ""
