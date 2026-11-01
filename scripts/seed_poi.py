"""
POI 数据拉取 & RAG 注入脚本 — 景点 + 餐厅 + 酒店

用法：
    python scripts/seed_poi.py --city 北京
"""

import argparse
import asyncio
import os
import re
import sys

from sqlalchemy import and_, or_, select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.db.models.attraction import Attraction
from app.db.models.restaurant import Restaurant
from app.db.models.hotel import Hotel
from app.db.session import async_session_factory, engine
from app.services.map.amap import AmapService
from app.services.vector.rebuild import rebuild_vector_index
from app.services.vector.vector_store import acquire_vector_lock


# ---- 坐标/评分/价格解析 ----

def _parse_coord(loc: str) -> tuple:
    if not loc: return None, None
    parts = loc.split(",")
    if len(parts) == 2:
        try: return float(parts[1]), float(parts[0])
        except: pass
    return None, None


def _parse_rating(poi: dict) -> float:
    try: return float((poi.get("biz_ext") or {}).get("rating", 0) or 0)
    except: return 0.0


def _parse_cost(poi: dict) -> float:
    try: return float((poi.get("biz_ext") or {}).get("cost", 0) or 0)
    except: return 0.0


def _parse_star(poi: dict) -> int:
    """尝试从标签或名称推断星级"""
    name = poi.get("name", "")
    tag = poi.get("tag", "") or ""
    text = name + tag
    for s in [5, 4, 3, 2, 1]:
        if f"{s}星" in text or f"{s}级" in text:
            return s
    return 3  # 默认三星


def _parse_tags(poi: dict) -> list[str]:
    raw = poi.get("tag", "") or ""
    return [t.strip() for t in raw.split(";") if t.strip()]


def _normalize_name(name: str) -> str:
    text = str(name or "").replace("（", "(").replace("）", ")")
    text = text.split("(", 1)[0]
    return re.sub(r"\s+", "", text).lower()


def _poi_identity(poi: dict) -> str | None:
    value = str(poi.get("id") or "").strip()
    return value or None


# ---- 拉取函数 ----

async def fetch_attractions(city: str, amap: AmapService) -> list[dict]:
    print("  [景点] 搜索中...")
    all_pois = []
    for kw, code in [("风景名胜", "110100"), ("博物馆", "140000"), ("公园广场", "110000"),
                      ("寺庙教堂", "110200"), ("游乐园", "080300")]:
        try:
            pois = await amap.search_poi(keywords=kw, city=city, types=code, offset=25)
            print(f"    {kw}: {len(pois)}")
            all_pois.extend(pois)
        except Exception as e:
            print(f"    {kw}: 超时跳过")
    return _dedupe_pois(all_pois)


async def fetch_restaurants(city: str, amap: AmapService) -> list[dict]:
    print("  [餐厅] 搜索中...")
    all_pois = []
    for kw in ["中餐", "火锅", "川菜", "粤菜", "日料", "西餐", "烧烤", "小吃快餐"]:
        try:
            pois = await amap.search_poi(keywords=kw, city=city, types="050000", offset=25)
            print(f"    {kw}: {len(pois)}")
            all_pois.extend(pois)
        except:
            print(f"    {kw}: 超时跳过")
    return _dedupe_pois(all_pois)


async def fetch_hotels(city: str, amap: AmapService) -> list[dict]:
    """从高德拉取酒店 — 住宿服务 POI"""
    print("  [酒店] 搜索中...")
    all_pois = []
    for kw in ["星级酒店", "快捷酒店", "商务酒店", "精品民宿", "青年旅舍"]:
        try:
            pois = await amap.search_poi(keywords=kw, city=city, types="060000", offset=25)
            print(f"    {kw}: {len(pois)}")
            all_pois.extend(pois)
        except:
            print(f"    {kw}: 超时跳过")
    result = []
    for poi in _dedupe_pois(all_pois):
        name = poi["name"]
        if any(kw in name for kw in ["酒店", "宾馆", "旅社", "民宿", "饭店", "客栈", "度假", "公寓"]):
            result.append(poi)
    print(f"    过滤后: {len(result)}")
    return result


def _dedupe_pois(pois: list[dict]) -> list[dict]:
    seen = set()
    result = []
    for poi in pois:
        name = str(poi.get("name") or "").strip()
        if not name:
            continue
        key = _poi_identity(poi) or _normalize_name(name)
        if key in seen:
            continue
        seen.add(key)
        result.append(poi)
    return result


def _update_attraction(item: Attraction, poi: dict, city: str) -> None:
    latitude, longitude = _parse_coord(poi.get("location", ""))
    item.name = poi["name"]
    item.city = city
    item.category = poi.get("type", "")
    item.latitude = latitude
    item.longitude = longitude
    item.address = poi.get("address", "")
    item.rating = _parse_rating(poi)
    item.price = _parse_cost(poi)
    item.tags = _parse_tags(poi)
    item.recommended_duration = item.recommended_duration or 2.0


def _update_restaurant(item: Restaurant, poi: dict, city: str) -> None:
    latitude, longitude = _parse_coord(poi.get("location", ""))
    item.name = poi["name"]
    item.city = city
    item.cuisine = poi.get("type", "")
    item.latitude = latitude
    item.longitude = longitude
    item.address = poi.get("address", "")
    item.rating = _parse_rating(poi)
    item.avg_price = _parse_cost(poi)
    item.tags = _parse_tags(poi)


def _update_hotel(item: Hotel, poi: dict, city: str) -> None:
    latitude, longitude = _parse_coord(poi.get("location", ""))
    item.name = poi["name"]
    item.city = city
    item.star = _parse_star(poi)
    item.latitude = latitude
    item.longitude = longitude
    item.address = poi.get("address", "")
    item.rating = _parse_rating(poi)
    item.price_per_night = _parse_cost(poi)
    item.amenities = _parse_tags(poi)


async def _upsert_pois(
    model: type,
    city: str,
    pois: list[dict],
    update_item,
) -> int:
    async with async_session_factory() as db:
        source_ids = [identity for poi in pois if (identity := _poi_identity(poi))]
        existing_filter = model.city == city
        if source_ids:
            existing_filter = or_(
                existing_filter,
                and_(
                    model.source == "amap",
                    model.source_poi_id.in_(source_ids),
                ),
            )
        existing = list((await db.execute(
            select(model).where(existing_filter)
        )).scalars().all())
        new_items, changed = _merge_pois(
            model, existing, city, pois, update_item
        )
        db.add_all(new_items)

        await db.commit()
        return changed


def _merge_pois(
    model: type,
    existing: list,
    city: str,
    pois: list[dict],
    update_item,
) -> tuple[list, int]:
    """Apply an Amap batch to loaded rows and return newly created rows."""
    by_source_id = {
        item.source_poi_id: item
        for item in existing
        if item.source == "amap" and item.source_poi_id
    }
    unclaimed_by_name = {
        _normalize_name(item.name): item
        for item in existing
        if not item.source_poi_id
    }

    new_items = []
    for poi in pois:
        source_poi_id = _poi_identity(poi)
        item = by_source_id.get(source_poi_id) if source_poi_id else None
        if item is None:
            item = unclaimed_by_name.pop(_normalize_name(poi["name"]), None)
        if item is None:
            item = model()
            new_items.append(item)

        item.source = "amap"
        item.source_poi_id = source_poi_id
        update_item(item, poi, city)
        if source_poi_id:
            by_source_id[source_poi_id] = item

    return new_items, len(pois)


# ---- 主流程 ----

async def seed_city(city: str, maintenance_lock=None):
    if maintenance_lock is None:
        with acquire_vector_lock() as acquired_lock:
            return await seed_city(city, maintenance_lock=acquired_lock)

    print(f"\n{'='*50}")
    print(f"  开始拉取：{city}")
    print(f"{'='*50}")

    if not settings.AMAP_API_KEY:
        print("错误：AMAP_API_KEY 未配置"); return

    amap = AmapService()

    # 1. 拉取
    print("\n[1/3] 从高德拉取数据")
    raw_attr = await fetch_attractions(city, amap)
    raw_rest = await fetch_restaurants(city, amap)
    raw_hotels = await fetch_hotels(city, amap)
    print(f"  总计: 景点{len(raw_attr)} | 餐厅{len(raw_rest)} | 酒店{len(raw_hotels)}")

    # 2. PostgreSQL 是 POI 真源：按高德 ID 幂等更新
    print("\n[2/3] 写入 PostgreSQL")
    attr_count = await _upsert_pois(Attraction, city, raw_attr, _update_attraction)
    rest_count = await _upsert_pois(Restaurant, city, raw_rest, _update_restaurant)
    hotel_count = await _upsert_pois(Hotel, city, raw_hotels, _update_hotel)

    print(f"  入库: 景点{attr_count} | 餐厅{rest_count} | 酒店{hotel_count}")

    # 3. PostgreSQL 更新完成后，全量构建影子索引并原子切换
    print("\n[3/3] 安全重建 Chroma 索引")
    result = await rebuild_vector_index(maintenance_lock=maintenance_lock)
    print(f"  集合数量: {result.counts}")
    if result.backup_dir is not None:
        print(f"  旧索引备份: {result.backup_dir}")

    print(f"\n  完成！景点{attr_count} | 餐厅{rest_count} | 酒店{hotel_count}")


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", default="北京")
    args = parser.parse_args()
    try:
        await seed_city(args.city)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    event_loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(event_loop)
        event_loop.run_until_complete(main())
    finally:
        event_loop.close()
        asyncio.set_event_loop(None)
