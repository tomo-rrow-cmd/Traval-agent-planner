"""
方案相关数据结构
"""

from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class PlanCreateRequest(BaseModel):
    """触发方案生成请求"""

    session_id: str = Field(..., description="会话 ID")
    confirmed: bool = Field(default=False, description="用户是否已确认开始生成方案")


class PlanDraftRequest(BaseModel):
    """开发态直接创建方案请求"""

    destination: str = Field(default="待确认", description="目的地城市")
    start_date: Optional[date] = Field(default=None, description="出发日期")
    end_date: Optional[date] = Field(default=None, description="返程日期")
    budget: float = Field(default=0, description="总预算（元）")
    travelers: int = Field(default=1, description="出行人数")
    preferences: Optional[list[str]] = Field(default=None, description="偏好标签")


class Location(BaseModel):
    """经纬度"""

    lat: Optional[float] = None
    lng: Optional[float] = None


class Activity(BaseModel):
    """行程活动"""

    time_slot: Optional[str] = None
    type: str = "rest"
    title: str
    subtitle: Optional[str] = None
    description: Optional[str] = None
    location: Optional[Location] = None
    duration_minutes: Optional[int] = None
    cost: float = 0
    rating: Optional[float] = None
    tags: list[str] = Field(default_factory=list)
    tips: Optional[str] = None


class Accommodation(BaseModel):
    """住宿信息"""

    hotel_name: Optional[str] = None
    address: Optional[str] = None
    room_type: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[float] = None
    check_in: Optional[str] = None
    check_out: Optional[str] = None
    location: Optional[Location] = None


class DailyItinerary(BaseModel):
    """每日行程"""

    day: int
    date: Optional[str] = None
    date_label: Optional[str] = None
    weather_summary: Optional[str] = None
    activities: list[Activity] = Field(default_factory=list)
    accommodation: Optional[Accommodation] = None
    meals: list[dict[str, Any]] = Field(default_factory=list)
    day_cost: float = 0
    day_summary: Optional[str] = None


class PlanOverview(BaseModel):
    """方案概览"""

    highlights: list[str] = Field(default_factory=list)
    total_distance_km: float = 0
    transport_modes: list[str] = Field(default_factory=list)


class WeatherForecast(BaseModel):
    """天气预报"""

    date: Optional[str] = None
    weather: Optional[str] = None
    temp_high: Optional[int] = None
    temp_low: Optional[int] = None
    wind: Optional[str] = None
    humidity: Optional[int] = None
    precipitation: Optional[float] = None
    aqi: Optional[int] = None
    advice: Optional[str] = None


class PlanSaveResult(BaseModel):
    """保存方案结果"""

    id: str
    saved_at: Optional[datetime] = None


class PlanFromDataRequest(BaseModel):
    """从本地缓存数据创建方案（local_xxx → 后端持久化）"""

    title: str = "未命名旅行方案"
    destination: str = ""
    departure: str = ""
    start_date: date
    end_date: date
    days: int = 0
    budget: float = 0
    estimated_cost: float = 0
    travelers: int = 1
    crowd_type: str = ""
    travel_style: str = ""
    preferences: list[str] = Field(default_factory=list)
    full_data: dict[str, Any] = Field(default_factory=dict)


class PlanSummary(BaseModel):
    """方案列表摘要"""

    id: str
    title: str = "未命名旅行方案"
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: int = 0
    estimated_cost: float = 0
    travel_style: Optional[str] = None
    status: str = "draft"
    is_favorite: bool = False
    saved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class PlanResponse(BaseModel):
    """方案详情响应"""

    id: str
    title: str = "未命名旅行方案"
    destination: Optional[str] = None
    departure: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: int = 0
    people_count: int = 1
    crowd_type: Optional[str] = None
    total_budget: float = 0
    estimated_cost: float = 0
    travel_style: Optional[str] = None
    status: str = "draft"
    version: int = 1
    is_favorite: bool = False
    saved_at: Optional[datetime] = None
    view_count: int = 0
    overview: PlanOverview = Field(default_factory=PlanOverview)
    daily_itinerary: list[DailyItinerary] = Field(default_factory=list)
    traffic_summary: dict[str, Any] = Field(default_factory=dict)
    food_summary: dict[str, Any] = Field(default_factory=dict)
    budget_detail: dict[str, Any] = Field(default_factory=dict)
    souvenir_recommendations: list[dict[str, Any]] = Field(default_factory=list)
    weather_forecast: list[WeatherForecast] = Field(default_factory=list)
    packing_list: list[str] = Field(default_factory=list)
    tips: list[str] = Field(default_factory=list)
    avoid_list: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # ====== 原始 pipeline 数据（供 PlanPreview/PlanDetailPage 前端直接使用） ======
    # 原始交通数据（含 daily_traffic, segments, options, time_warnings）
    traffic: dict[str, Any] = Field(default_factory=dict)
    # 住宿推荐（含 recommendations, selected, 通勤评分）
    hotel_plan: dict[str, Any] = Field(default_factory=dict)
    # 城际交通（火车/航班列表）
    big_traffic: list[dict[str, Any]] = Field(default_factory=list)
    # 原始预算数据（含 details, warnings, suggestions）
    budget: dict[str, Any] = Field(default_factory=dict)
    # 每日餐饮计划
    meal_plan: list[dict[str, Any]] = Field(default_factory=list)
    # 景点深度详情
    attraction_details: list[dict[str, Any]] = Field(default_factory=list)
    # 美食深度详情
    food_details: list[dict[str, Any]] = Field(default_factory=list)
    # 天气影响因子
    weather_impact: list[dict[str, Any]] = Field(default_factory=list)
    # 人均日花费
    per_person_per_day: float = 0
    # 行程节奏
    pace: str = ""
    # 完整原始数据（final_plan JSON）
    full_data: dict[str, Any] = Field(default_factory=dict)


class PlanModification(BaseModel):
    """方案局部修改项"""

    type: str
    day: Optional[int] = None
    activity_index: Optional[int] = None
    target_type: Optional[str] = None
    reason: Optional[str] = None
    constraints: dict[str, Any] = Field(default_factory=dict)
    constraint: Optional[str] = None


class PlanModifyRequest(BaseModel):
    """局部修改方案请求"""

    modifications: list[PlanModification]


class PlanRegenerateRequest(BaseModel):
    """重新生成方案请求"""

    session_id: str
    confirmed: bool = Field(default=False, description="用户是否已确认重新生成方案")


class PlanShareRequest(BaseModel):
    """分享方案请求"""

    expire_in: Optional[int] = None
    password: Optional[str] = None


class PlanShareResult(BaseModel):
    """分享方案结果"""

    share_url: str
    expire_at: Optional[datetime] = None


class PlanFavoriteResult(BaseModel):
    """收藏切换结果"""

    is_favorite: bool


class PlanExportTask(BaseModel):
    """异步导出任务"""

    task_id: str
    status: str = "processing"
    estimated_wait_seconds: int = 15
