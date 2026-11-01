"""
工具注册中心 — 真正可执行的 Function Calling 工具

Agent 调用 call_llm_with_tools → DeepSeek 返回 tool_call →
执行工具函数 → 结果回传 LLM → 生成最终回复

流程：
    1. Agent 构建 messages + tools → LLM
    2. LLM 返回 tool_calls → 解析 tool_name + arguments
    3. 查找注册表 → 执行异步函数
    4. 结果追加到 messages → 再次调 LLM → 最终输出
"""

from typing import Any, Callable

# 全局工具注册表
_registry: dict[str, dict] = {}


def register(name: str, description: str, parameters: dict, handler: Callable):
    """
    注册一个工具。

    Args:
        name: 工具名（DeepSeek 用这个名字来调用）
        description: 功能描述
        parameters: JSON Schema 格式的参数定义
        handler: async callable，真正执行的函数
    """
    _registry[name] = {
        "name": name,
        "description": description,
        "parameters": parameters,
        "handler": handler,
    }


def get_tool_defs() -> list[dict]:
    """获取所有注册工具的定义列表（给 LLM 的 tools 参数）"""
    return [{
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["parameters"],
        },
    } for t in _registry.values()]


def get_handler(name: str) -> Callable | None:
    """根据工具名获取执行函数"""
    t = _registry.get(name)
    return t["handler"] if t else None


# ============================================================
#  已注册的工具
# ============================================================

async def _search_attractions(city: str, keywords: str = "", limit: int = 20) -> dict:
    """
    真正的景点搜索工具 — 先查 Chroma RAG，不够再查 PostgreSQL。
    """
    from app.services.vector.rag import rag_search

    query = f"在{city}，{keywords or '热门景点推荐'}"
    try:
        candidates = await rag_search(
            "attractions",
            query,
            where={"city": city},
            final_k=max(1, int(limit or 20)),
        )
    except Exception as e:
        print(f"  [Tool RAG attractions] 失败: {e}")
        candidates = []

    attractions = []
    for item in candidates:
        attraction = {
            "name": item.get("name", item.get("id", "")),
            "rating": item.get("rating", 0),
            "price": item.get("price", 0),
            "tags": item.get("tags", ""),
            "address": item.get("address", ""),
            "relevance": item.get("relevance", 0),
        }
        if item.get("rerank_score") is not None:
            attraction["rerank_score"] = item["rerank_score"]
        attractions.append(attraction)

    return {"count": len(attractions), "attractions": attractions}


async def _search_restaurants(city: str, cuisine: str = "", budget: float = 0, limit: int = 20) -> dict:
    """真正的餐厅搜索工具 — Chroma RAG"""
    from app.services.vector.rag import rag_search

    query = f"在{city}，{cuisine or '热门美食'}，人均{'¥' + str(int(budget)) + '以内' if budget > 0 else ''}"
    try:
        candidates = await rag_search(
            "restaurants",
            query,
            where={"city": city},
            final_k=max(1, int(limit or 20)),
        )
    except Exception as e:
        print(f"  [Tool RAG restaurants] 失败: {e}")
        candidates = []

    restaurants = []
    for item in candidates:
        restaurant = {
            "name": item.get("name", item.get("id", "")),
            "cuisine": item.get("cuisine", ""),
            "rating": item.get("rating", 0),
            "avg_price": item.get("avg_price", 0),
            "tags": item.get("tags", ""),
            "relevance": item.get("relevance", 0),
        }
        if item.get("rerank_score") is not None:
            restaurant["rerank_score"] = item["rerank_score"]
        restaurants.append(restaurant)

    return {"count": len(restaurants), "restaurants": restaurants}


async def _search_hotels(city: str, min_star: int = 3, max_price: float = 0, limit: int = 20) -> dict:
    """真正的酒店搜索工具 — Chroma RAG + Amap 详情价格"""
    from app.services.vector.rag import rag_search
    from app.services.map.amap import AmapService

    query = f"在{city}，{min_star}星级以上酒店"
    try:
        candidates = await rag_search(
            "hotels",
            query,
            where={"city": city},
            final_k=max(1, int(limit or 20)),
        )
    except Exception as e:
        print(f"  [Tool RAG hotels] 失败: {e}")
        candidates = []

    hotels = []
    for item in candidates:
        # 尝试从高德详情获取真实价格
        real_price = item.get("price_per_night", 0)
        if real_price <= 0:
            try:
                amap = AmapService()
                detail = await amap.search_poi(keywords=item.get("name", ""), city=city, offset=1)
                if detail:
                    cost = float((detail[0].get("biz_ext") or {}).get("cost", 0) or 0)
                    if cost > 0:
                        real_price = cost
            except Exception:
                pass

        hotel = {
            "name": item.get("name", item.get("id", "")),
            "star": item.get("star", 3),
            "rating": item.get("rating", 0),
            "price_per_night": round(real_price, 2) if real_price > 0 else 0,
            "price_verified": real_price > 0,  # 标记价格是否真实
            "relevance": item.get("relevance", 0),
        }
        if item.get("rerank_score") is not None:
            hotel["rerank_score"] = item["rerank_score"]
        hotels.append(hotel)

    return {"count": len(hotels), "hotels": hotels}


async def _get_weather(city: str, start_date: str = "", end_date: str = "") -> dict:
    """天气查询工具 — 高德天气 API"""
    from app.services.weather.qweather import qweather_service
    from datetime import date

    try:
        current = await qweather_service.get_current_weather(city)
        if start_date and end_date:
            sd = date.fromisoformat(start_date)
            ed = date.fromisoformat(end_date)
            forecasts = await qweather_service.get_forecast_for_dates(city, sd, ed)
        else:
            forecasts = await qweather_service.get_7day_forecast(city)
        return {"current": current, "forecasts": forecasts}
    except Exception as e:
        return {"error": str(e)}


async def _get_route(origin_lat: float, origin_lng: float,
                     dest_lat: float, dest_lng: float,
                     mode: str = "transit") -> dict:
    """路径规划工具 — 高德 direction API"""
    from app.services.map.amap import AmapService

    origin = f"{origin_lng},{origin_lat}"
    destination = f"{dest_lng},{dest_lat}"
    try:
        amap = AmapService()
        route = await amap.route_planning(origin, destination, mode)
        return {"route": route}
    except Exception as e:
        return {"error": str(e)}


# ---- 注册 ----

register(
    "search_attractions", "搜索指定城市的景点，按关键词和偏好匹配",
    {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"},
            "keywords": {"type": "string", "description": "搜索关键词，如 历史人文、亲子"},
            "limit": {"type": "integer", "description": "返回数量，默认20"},
        },
        "required": ["city"],
    },
    _search_attractions,
)

register(
    "search_restaurants", "搜索指定城市的餐厅，按菜系和预算过滤",
    {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"},
            "cuisine": {"type": "string", "description": "菜系，如 川菜、火锅"},
            "budget": {"type": "number", "description": "人均预算上限"},
            "limit": {"type": "integer", "description": "返回数量，默认20"},
        },
        "required": ["city"],
    },
    _search_restaurants,
)

register(
    "search_hotels", "搜索指定城市的酒店，按星级和预算过滤，价格来自真实数据",
    {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"},
            "min_star": {"type": "integer", "description": "最低星级"},
            "max_price": {"type": "number", "description": "每晚最高价格"},
            "limit": {"type": "integer", "description": "返回数量，默认20"},
        },
        "required": ["city"],
    },
    _search_hotels,
)

register(
    "get_weather", "获取城市天气（实时+预报）",
    {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"},
            "start_date": {"type": "string", "description": "起始日期 YYYY-MM-DD"},
            "end_date": {"type": "string", "description": "结束日期 YYYY-MM-DD"},
        },
        "required": ["city"],
    },
    _get_weather,
)

register(
    "get_route", "获取两点间的真实路径规划",
    {
        "type": "object",
        "properties": {
            "origin_lat": {"type": "number", "description": "起点纬度"},
            "origin_lng": {"type": "number", "description": "起点经度"},
            "dest_lat": {"type": "number", "description": "终点纬度"},
            "dest_lng": {"type": "number", "description": "终点经度"},
            "mode": {"type": "string", "description": "transit/driving/walking"},
        },
        "required": ["origin_lat", "origin_lng", "dest_lat", "dest_lng"],
    },
    _get_route,
)

# ---- 美团酒旅 Skill 工具（CLI 方式） ----

async def _meituan_query(city: str, query: str) -> dict:
    """美团酒旅 Skill — 酒店/景点/行程一站式查询"""
    from app.services.third_party.meituan import meituan
    result = await meituan.query(city, query)
    if result.get("success"):
        return {"text": result["text"], "city": city, "source": "meituan"}
    return {"error": result.get("error", "unknown"), "text": result.get("text", "")}


register(
    "meituan_travel", "美团酒旅 Skill：搜酒店(真实价格+评分)、搜景点门票、规划行程、查火车票。一站式旅行查询。",
    {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"},
            "query": {"type": "string", "description": "自然语言查询，越具体越好。如：故宫附近500以内酒店、推荐必去景点、3日游行程"},
        },
        "required": ["city", "query"],
    },
    _meituan_query,
)

# ---- 12306 火车票工具 ----

async def _railway_trains(from_city: str, to_city: str, date: str = "") -> dict:
    """12306 余票查询"""
    from app.services.third_party.railway12306 import railway
    trains = railway.query_all_trains(from_city, to_city, date)
    return {"count": len(trains), "trains": trains[:20], "source": "12306"}


async def _railway_price(train_no: str, from_city: str, to_city: str, date: str = "") -> dict:
    """12306 票价查询"""
    from app.services.third_party.railway12306 import railway
    trains = railway.query_all_trains(from_city, to_city, date)
    train = next((item for item in trains if item.get("trainNo") == train_no), None)
    if train is None:
        return {"prices": {}, "source": "12306", "error": "train_not_found"}
    prices = railway.query_price(
        train_no,
        train.get("fromStationNo", ""),
        train.get("toStationNo", ""),
        date,
        train.get("seatTypes", ""),
    )
    return {"prices": prices, "source": "12306"}


async def _railway_stops(train_no: str, from_city: str, to_city: str, date: str = "") -> dict:
    """12306 经停站查询"""
    from app.services.third_party.railway12306 import railway
    stops = railway.query_stops(train_no, from_city, to_city, date)
    return {"count": len(stops), "stops": stops, "source": "12306"}


register(
    "railway_search_trains", "12306 火车票查询 — 两站间全部车次+余票+时间",
    {
        "type": "object",
        "properties": {
            "from_city": {"type": "string", "description": "出发城市"},
            "to_city": {"type": "string", "description": "到达城市"},
            "date": {"type": "string", "description": "日期 YYYY-MM-DD"},
        },
        "required": ["from_city", "to_city"],
    },
    _railway_trains,
)

register(
    "railway_query_price", "12306 票价查询 — 指定车次的各座位类型价格",
    {
        "type": "object",
        "properties": {
            "train_no": {"type": "string", "description": "12306内部车次编号"},
            "from_city": {"type": "string", "description": "出发城市"},
            "to_city": {"type": "string", "description": "到达城市"},
            "date": {"type": "string", "description": "日期 YYYY-MM-DD"},
        },
        "required": ["train_no", "from_city", "to_city"],
    },
    _railway_price,
)

register(
    "railway_query_stops", "12306 经停站查询 — 列车沿途停靠站点",
    {
        "type": "object",
        "properties": {
            "train_no": {"type": "string", "description": "12306内部车次编号"},
            "from_city": {"type": "string", "description": "出发城市"},
            "to_city": {"type": "string", "description": "到达城市"},
            "date": {"type": "string", "description": "日期 YYYY-MM-DD"},
        },
        "required": ["train_no", "from_city", "to_city"],
    },
    _railway_stops,
)
