"""基础数据接口 schema"""

from datetime import date as _Date
from typing import Optional

from pydantic import BaseModel, Field


class City(BaseModel):
    """城市数据"""

    id: str
    name: str
    province: Optional[str] = None
    country: str = "中国"
    name_en: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    level: Optional[str] = None
    popular_rank: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    description: Optional[str] = None


class AttractionData(BaseModel):
    """景点数据"""

    id: str
    name: str
    city: str
    address: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    level: Optional[str] = None
    rating: Optional[float] = None
    review_count: int = 0
    ticket_price: Optional[str] = None
    open_time: Optional[str] = None
    suggest_duration: Optional[int] = None
    tags: list[str] = Field(default_factory=list)
    best_time: Optional[str] = None
    highlights: Optional[str] = None
    tips: Optional[str] = None
    image_url: Optional[str] = None


class RestaurantData(BaseModel):
    """餐厅数据"""

    id: str
    name: str
    city: str
    address: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    cuisine: Optional[str] = None
    avg_price: Optional[float] = None
    rating: Optional[float] = None
    recommended_dishes: list[str] = Field(default_factory=list)
    open_time: Optional[str] = None
    need_booking: bool = False
    tags: list[str] = Field(default_factory=list)
    tips: Optional[str] = None


class HotelData(BaseModel):
    """酒店数据"""

    id: str
    name: str
    city: str
    address: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    star_level: Optional[int] = None
    rating: Optional[float] = None
    price: Optional[float] = None
    room_types: list[str] = Field(default_factory=list)
    facilities: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    distance_to_center_km: Optional[float] = None


class WeatherItem(BaseModel):
    """天气项"""

    date: Optional[_Date] = None
    weather: str = "未知"
    temp_high: Optional[int] = None
    temp_low: Optional[int] = None
    wind: Optional[str] = None
    humidity: Optional[int] = None
    precipitation: Optional[float] = None
    aqi: Optional[int] = None
    advice: Optional[str] = None


class WeatherData(BaseModel):
    """天气查询结果"""

    city: str
    forecasts: list[WeatherItem] = Field(default_factory=list)
