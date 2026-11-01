"""PostgreSQL POI rows to Chroma index documents and metadata."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any

from app.db.models.attraction import Attraction
from app.db.models.hotel import Hotel
from app.db.models.restaurant import Restaurant


@dataclass(frozen=True)
class CollectionSpec:
    name: str
    model: type
    document_builder: Callable[[Any], str]
    metadata_builder: Callable[[Any], dict[str, Any]]


def _join(values: Iterable[Any] | None) -> str:
    if not values:
        return ""
    return ";".join(str(value) for value in values if value)


def _clean_meta(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return _join(value)
    return str(value)


def _metadata(item: Any, values: dict[str, Any]) -> dict[str, Any]:
    common = {
        "name": item.name,
        "city": item.city,
        "source": item.source,
        "source_poi_id": item.source_poi_id,
        "latitude": item.latitude,
        "longitude": item.longitude,
        "address": item.address,
    }
    return {key: _clean_meta(value) for key, value in {**common, **values}.items()}


def _attraction_doc(item: Attraction) -> str:
    return (
        f"名称：{item.name}。城市：{item.city}。类型：{item.category or ''}。"
        f"标签：{_join(item.tags)}。地址：{item.address or ''}。"
        f"评分：{item.rating or 0}。门票：{item.price or 0}。"
        f"推荐游玩时长：{item.recommended_duration or 0}小时。"
        f"简介：{item.description or ''}"
    )


def _attraction_meta(item: Attraction) -> dict[str, Any]:
    return _metadata(item, {
        "category": item.category,
        "rating": item.rating,
        "price": item.price,
        "tags": item.tags,
    })


def _restaurant_doc(item: Restaurant) -> str:
    return (
        f"名称：{item.name}。城市：{item.city}。菜系：{item.cuisine or ''}。"
        f"标签：{_join(item.tags)}。地址：{item.address or ''}。"
        f"评分：{item.rating or 0}。人均：{item.avg_price or 0}。"
        f"营业时间：{item.opening_hours or ''}。简介：{item.description or ''}"
    )


def _restaurant_meta(item: Restaurant) -> dict[str, Any]:
    return _metadata(item, {
        "cuisine": item.cuisine,
        "rating": item.rating,
        "avg_price": item.avg_price,
        "tags": item.tags,
    })


def _hotel_doc(item: Hotel) -> str:
    return (
        f"名称：{item.name}。城市：{item.city}。星级：{item.star or 0}。"
        f"设施：{_join(item.amenities)}。地址：{item.address or ''}。"
        f"评分：{item.rating or 0}。每晚价格：{item.price_per_night or 0}。"
        f"简介：{item.description or ''}"
    )


def _hotel_meta(item: Hotel) -> dict[str, Any]:
    return _metadata(item, {
        "star": item.star,
        "rating": item.rating,
        "price_per_night": item.price_per_night,
        "tags": item.amenities,
    })


POI_INDEX_SPECS = (
    CollectionSpec("attractions", Attraction, _attraction_doc, _attraction_meta),
    CollectionSpec("restaurants", Restaurant, _restaurant_doc, _restaurant_meta),
    CollectionSpec("hotels", Hotel, _hotel_doc, _hotel_meta),
)
