"""
Agent 输出 Schema — Pydantic 校验，防止字段缺失导致下游崩盘
"""

from typing import Optional

from pydantic import BaseModel, Field


# ---- 景点 Agent ----

class AttractionItem(BaseModel):
    poi_id: Optional[str] = None
    source: Optional[str] = None
    source_poi_id: Optional[str] = None
    name: str
    reason: str = ""
    duration_hours: float = 2.0
    poi_id: Optional[str] = None
    source: Optional[str] = None
    source_poi_id: Optional[str] = None
    rating: float = 0
    price: float = 0
    rating: float = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    category: Optional[str] = None
    tags: Optional[str] = None

class DayPlan(BaseModel):
    day: int
    attractions: list[AttractionItem] = Field(default_factory=list)

class AttractionOutput(BaseModel):
    attractions: list[dict] = Field(default_factory=list)
    daily_plan: list[DayPlan] = Field(default_factory=list)
    candidate_count: int = 0
    message: Optional[str] = None


# ---- 美食 Agent ----

class MealItem(BaseModel):
    poi_id: Optional[str] = None
    source: Optional[str] = None
    source_poi_id: Optional[str] = None
    meal: str = "午餐"
    restaurant: str = ""
    reason: str = ""
    avg_price: float = 0
    rating: float = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None

class MealDay(BaseModel):
    day: int
    meals: list[MealItem] = Field(default_factory=list)

class FoodOutput(BaseModel):
    restaurants: list[dict] = Field(default_factory=list)
    meal_plan: list[MealDay] = Field(default_factory=list)
    candidate_count: int = 0
    message: Optional[str] = None


# ---- 住宿 Agent ----

class HotelRec(BaseModel):
    poi_id: Optional[str] = None
    source: Optional[str] = None
    source_poi_id: Optional[str] = None
    name: str
    reason: str = ""
    price_per_night: float = 0
    estimated: bool = False
    price_verified: bool = False
    price_source: Optional[str] = None
    nights: int = 1
    total: float = 0
    rating: float = 0
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    coordinates_available: bool = False
    commute_score: Optional[float] = None
    commute_confidence: Optional[str] = None
    commute_note: Optional[str] = None

class HotelPlan(BaseModel):
    recommendations: list[HotelRec] = Field(default_factory=list)
    selected: Optional[str] = None
    selected_hotel: Optional[HotelRec] = None
    selection_reason: str = ""
    summary: str = ""

class HotelOutput(BaseModel):
    hotels: list[dict] = Field(default_factory=list)
    hotel_plan: HotelPlan = Field(default_factory=HotelPlan)
    message: Optional[str] = None


# ---- 预算 Agent ----

class BudgetDetail(BaseModel):
    category: str
    budget: float = 0
    spent: float = 0
    remaining: float = 0
    status: str = "ok"

class BudgetOutput(BaseModel):
    total_budget: float = 0
    budget_allocation: dict = {}
    actual_details: list[BudgetDetail] = []
    actual_total: float = 0
    remaining: float = 0
    per_person_per_day: float = 0
    warnings: list[str] = []


# ---- 交通 Agent ----

class TrafficSegment(BaseModel):
    from_: str = Field(default="", alias="from")
    to: str = Field(default="", alias="to")
    distance_km: float = 0
    time_min: int = 0
    cost: float = 0
    mode: str = "transit"

    class Config:
        populate_by_name = True

class TrafficDay(BaseModel):
    day: int
    segments: list[dict] = []
    total_time_min: int = 0
    total_cost: float = 0

class TrafficOutput(BaseModel):
    daily_traffic: list[TrafficDay] = []
    total_traffic_cost: float = 0
    summary: str = ""


# ---- 纪念品 Agent ----

class SouvenirItem(BaseModel):
    name: str
    category: str = ""
    price_range: str = ""
    buy_place: str = ""
    reason: str = ""
    quantity_suggest: int = 1

class SouvenirOutput(BaseModel):
    souvenirs: list[SouvenirItem] = []
    total_estimate: float = 0
    message: Optional[str] = None


# ---- 天气 Agent ----

class WeatherOutput(BaseModel):
    weather_data: dict = {}
    suggestions: list[str] = []
    status: str = ""


# ---- 路线优化 Agent ----

class OptimizedDay(BaseModel):
    day: int
    attractions: list[dict] = []
    original_order: list[str] = []
    optimized_order: list[str] = []
    distance_before_km: float = 0
    distance_after_km: float = 0
    saved_km: float = 0
    saved_time_min: float = 0

class RouteOptimizerOutput(BaseModel):
    optimized_itinerary: list[OptimizedDay] = []
    total_saved_distance_km: float = 0
    suggestions: str = ""


# ---- 用户交互 Agent ----

class UserInteractionOutput(BaseModel):
    reply: str
    extracted: dict = {}
    ready: bool = False
