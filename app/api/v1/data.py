"""基础数据接口 - 契约 MVP 实现"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.attraction import Attraction
from app.db.models.hotel import Hotel
from app.db.models.restaurant import Restaurant
from app.dependencies import get_db
from app.schemas.common import BaseResponse, PaginatedData
from app.schemas.data import AttractionData, City, HotelData, RestaurantData, WeatherData, WeatherItem
from app.services.data.attraction_service import AttractionService
from app.services.data.hotel_service import HotelService
from app.services.data.restaurant_service import RestaurantService

router = APIRouter(prefix="/data", tags=["基础数据接口"])


def _parse_price_range(price_range: str | None) -> float | None:
    if not price_range:
        return None
    try:
        return float(price_range.split("-")[-1])
    except ValueError:
        return None


def _attraction_to_data(item: Attraction) -> AttractionData:
    return AttractionData(
        id=item.id,
        name=item.name,
        city=item.city,
        address=item.address,
        longitude=item.longitude,
        latitude=item.latitude,
        level=item.category,
        rating=item.rating,
        ticket_price="免费" if not item.price else str(item.price),
        open_time=item.opening_hours,
        suggest_duration=int((item.recommended_duration or 0) * 60) or None,
        tags=item.tags or [],
        highlights=item.description,
        image_url=item.image_url,
    )


def _restaurant_to_data(item: Restaurant) -> RestaurantData:
    return RestaurantData(
        id=item.id,
        name=item.name,
        city=item.city,
        address=item.address,
        longitude=item.longitude,
        latitude=item.latitude,
        cuisine=item.cuisine,
        avg_price=item.avg_price,
        rating=item.rating,
        open_time=item.opening_hours,
        tags=item.tags or [],
        tips=item.description,
    )


def _hotel_to_data(item: Hotel) -> HotelData:
    return HotelData(
        id=item.id,
        name=item.name,
        city=item.city,
        address=item.address,
        longitude=item.longitude,
        latitude=item.latitude,
        star_level=item.star,
        rating=item.rating,
        price=item.price_per_night,
        facilities=item.amenities or [],
        tags=[],
    )


@router.get("/cities", response_model=BaseResponse[list[City]])
async def list_cities(
    popular: bool | None = Query(default=None),
    keyword: str | None = Query(default=None),
):
    """获取热门城市或搜索城市。契约 MVP 返回内置展示数据。"""
    cities = [
        City(
            id="city_001",
            name="大理",
            province="云南",
            name_en="Dali",
            longitude=100.234,
            latitude=25.678,
            level="prefecture",
            popular_rank=12,
            tags=["历史名城", "自然风光", "休闲度假"],
            description="风花雪月，大理古城",
        )
    ]
    if keyword:
        cities = [city for city in cities if keyword in city.name]
    if popular is False:
        cities = []
    return BaseResponse(data=cities)


@router.get("/attractions", response_model=BaseResponse[PaginatedData[AttractionData]])
async def list_attractions(
    city: str,
    tags: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取景点列表"""
    service = AttractionService(db)
    tag_list = [tag for tag in (tags or "").split(",") if tag]
    items = await (
        service.search_by_tags(city=city, tags=tag_list, limit=page_size)
        if tag_list
        else service.search_by_city(city=city, limit=page_size)
    )
    data = [_attraction_to_data(item) for item in items]
    return BaseResponse(data=PaginatedData.create(data, total=len(data), page=page, page_size=page_size))


@router.get("/attractions/{item_id}", response_model=BaseResponse[AttractionData | None])
async def get_attraction(item_id: str, db: AsyncSession = Depends(get_db)):
    """获取景点详情"""
    item = await AttractionService(db).get_by_id(item_id)
    return BaseResponse(data=_attraction_to_data(item) if item else None)


@router.get("/restaurants", response_model=BaseResponse[PaginatedData[RestaurantData]])
async def list_restaurants(
    city: str,
    cuisine: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取餐厅列表"""
    items = await RestaurantService(db).search_by_city(city=city, cuisine=cuisine, limit=page_size)
    data = [_restaurant_to_data(item) for item in items]
    return BaseResponse(data=PaginatedData.create(data, total=len(data), page=page, page_size=page_size))


@router.get("/hotels", response_model=BaseResponse[PaginatedData[HotelData]])
async def list_hotels(
    city: str,
    price_range: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """获取酒店列表"""
    items = await HotelService(db).search_by_city(
        city=city,
        max_price=_parse_price_range(price_range),
        limit=page_size,
    )
    data = [_hotel_to_data(item) for item in items]
    return BaseResponse(data=PaginatedData.create(data, total=len(data), page=page, page_size=page_size))


@router.get("/weather", response_model=BaseResponse[WeatherData])
async def get_weather(
    city: str,
    forecast_date: date | None = Query(default=None, alias="date"),
):
    """查询天气。契约 MVP 不调用外部天气服务。"""
    forecast = WeatherItem(
        date=forecast_date,
        weather="未知",
        advice="契约 MVP 暂未接入真实天气服务",
    )
    return BaseResponse(data=WeatherData(city=city, forecasts=[forecast]))
