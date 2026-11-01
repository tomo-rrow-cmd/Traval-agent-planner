"""
POI 实时查询工具 — 高德即时搜索，替代 seed_poi.py subprocess 调用

供 AttractionAgent / FoodAgent / HotelAgent 在 RAG 数据不足时使用。
轻量、秒级返回、不写数据库。
"""

from app.services.map.amap import AmapService


# ---- 景点搜索 ----

ATTR_KEYWORDS = [
    ("风景名胜", "110100"), ("博物馆", "140000"), ("公园广场", "110000"),
    ("寺庙教堂", "110200"), ("游乐园", "080300"),
]

REST_KEYWORDS = ["中餐", "火锅", "川菜", "日料", "西餐", "烧烤", "小吃快餐", "粤菜"]

HOTEL_KEYWORDS = ["星级酒店", "快捷酒店", "商务酒店", "精品民宿", "青年旅舍"]


async def live_search_attractions(city: str, limit: int = 15) -> list[dict]:
    """高德实时搜索景点，返回 name/rating/price/lat/lng"""
    amap = AmapService()
    seen = set()
    results = []

    for kw, code in ATTR_KEYWORDS:
        if len(results) >= limit:
            break
        try:
            pois = await amap.search_poi(keywords=kw, city=city, types=code, offset=min(10, limit))
            for p in pois:
                name = p.get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    lat, lng = _parse_coord(p.get("location", ""))
                    results.append({
                        "name": name,
                        "rating": _parse_rating(p),
                        "price": _parse_cost(p),
                        "category": p.get("type", ""),
                        "tags": _parse_tags(p),
                        "address": p.get("address", ""),
                        "latitude": lat,
                        "longitude": lng,
                        "relevance": 0.6,
                        "source": "amap_live",
                    })
        except Exception:
            continue

    return results[:limit]


async def live_search_restaurants(city: str, limit: int = 15) -> list[dict]:
    """高德实时搜索餐厅"""
    amap = AmapService()
    seen = set()
    results = []

    for kw in REST_KEYWORDS:
        if len(results) >= limit:
            break
        try:
            pois = await amap.search_poi(keywords=kw, city=city, types="050000", offset=min(10, limit))
            for p in pois:
                name = p.get("name", "")
                if name and name not in seen:
                    seen.add(name)
                    lat, lng = _parse_coord(p.get("location", ""))
                    results.append({
                        "name": name,
                        "cuisine": p.get("type", ""),
                        "rating": _parse_rating(p),
                        "avg_price": _parse_cost(p),
                        "tags": _parse_tags(p),
                        "address": p.get("address", ""),
                        "latitude": lat,
                        "longitude": lng,
                        "relevance": 0.6,
                        "source": "amap_live",
                    })
        except Exception:
            continue

    return results[:limit]


async def live_search_hotels(city: str, limit: int = 10) -> list[dict]:
    """高德实时搜索酒店"""
    amap = AmapService()
    seen = set()
    results = []

    for kw in HOTEL_KEYWORDS:
        if len(results) >= limit:
            break
        try:
            pois = await amap.search_poi(keywords=kw, city=city, types="060000", offset=min(10, limit))
            for p in pois:
                name = p.get("name", "")
                if name and name not in seen:
                    # 过滤掉明显不是酒店的
                    if not any(k in name for k in ["酒店", "宾馆", "旅社", "民宿", "饭店", "客栈", "度假", "公寓"]):
                        continue
                    seen.add(name)
                    lat, lng = _parse_coord(p.get("location", ""))
                    results.append({
                        "name": name,
                        "star": _parse_star(p),
                        "rating": _parse_rating(p),
                        "price_per_night": _parse_cost(p),
                        "tags": _parse_tags(p),
                        "address": p.get("address", ""),
                        "latitude": lat,
                        "longitude": lng,
                        "relevance": 0.6,
                        "source": "amap_live",
                    })
        except Exception:
            continue

    return results[:limit]


# ---- 解析辅助 ----

def _parse_coord(loc: str) -> tuple:
    if not loc:
        return None, None
    parts = loc.split(",")
    if len(parts) == 2:
        try:
            return float(parts[1]), float(parts[0])
        except (ValueError, TypeError):
            pass
    return None, None


def _parse_rating(poi: dict) -> float:
    try:
        return float((poi.get("biz_ext") or {}).get("rating", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_cost(poi: dict) -> float:
    try:
        return float((poi.get("biz_ext") or {}).get("cost", 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _parse_tags(poi: dict) -> str:
    raw = poi.get("tag", "") or ""
    tags = [t.strip() for t in raw.split(";") if t.strip()]
    return ";".join(tags)


def _parse_star(poi: dict) -> int:
    name = poi.get("name", "")
    tag = poi.get("tag", "") or ""
    text = name + tag
    for s in [5, 4, 3, 2, 1]:
        if f"{s}星" in text or f"{s}级" in text:
            return s
    return 3
