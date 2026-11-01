"""
管线级缓存 — 单次 pipeline 执行中复用 RAG、地理编码、路线查询结果

避免同一规划中多个 Agent 重复查询相同数据，减少：
- Embedding 计算（模型推理）
- Chroma 向量检索
- 高德 API 调用（有 QPS 限制）

用法:
    cache = PipelineCache()
    result = await cache.rag("attractions", "北京故宫附近景点", prefer_cache=True)
"""

from typing import Any


class PipelineCache:
    """单次管线执行的短期缓存"""

    def __init__(self):
        self._rag: dict[str, list[dict]] = {}           # f"{collection}:{query}" → candidates
        self._geocode: dict[str, tuple[float, float]] = {}  # "名称" → (lat, lng)
        self._route: dict[str, dict] = {}                # f"{from_lng},{from_lat}→{to_lng},{to_lat}" → route
        self._weather: dict[str, dict] = {}              # "city" → weather data
        self._embedding: dict[str, list[float]] = {}     # query → embedding vector
        self._hits: dict[str, int] = {}                  # 统计各类命中次数

    # ========== RAG 缓存 ==========

    def rag_key(self, collection: str, query: str) -> str:
        return f"{collection}:{query}"

    async def rag_get(self, collection: str, query: str) -> list[dict] | None:
        key = self.rag_key(collection, query)
        return self._rag.get(key)

    async def rag_set(self, collection: str, query: str, candidates: list[dict]):
        key = self.rag_key(collection, query)
        self._rag[key] = candidates
        self._hits["rag_set"] = self._hits.get("rag_set", 0) + 1

    async def rag_search(self, collection: str, query: str, **kwargs) -> list[dict]:
        """带缓存的 RAG 检索"""
        cached = await self.rag_get(collection, query)
        if cached is not None:
            self._hits["rag_hit"] = self._hits.get("rag_hit", 0) + 1
            return cached

        from app.services.vector.rag import rag_search as _rag_search
        result = await _rag_search(collection, query, **kwargs)
        await self.rag_set(collection, query, result)
        return result

    # ========== 地理编码缓存 ==========

    async def geocode_get(self, name: str) -> tuple[float, float] | None:
        return self._geocode.get(name)

    async def geocode_set(self, name: str, lat: float, lng: float):
        self._geocode[name] = (lat, lng)
        self._hits["geocode_set"] = self._hits.get("geocode_set", 0) + 1

    async def geocode(self, name: str, city: str = "") -> tuple[float, float] | None:
        """带缓存的地理编码：名称 → (lat, lng)"""
        if name in self._geocode:
            self._hits["geocode_hit"] = self._hits.get("geocode_hit", 0) + 1
            return self._geocode[name]

        try:
            from app.services.map.amap import amap_service
            address = f"{city}{name}" if city else name
            result = await amap_service.geocode(address, city or None)
            if result:
                lat, lng = result["latitude"], result["longitude"]
                await self.geocode_set(name, lat, lng)
                return (lat, lng)
        except Exception:
            pass
        return None

    # ========== 路线缓存 ==========

    def route_key(self, from_lng: float, from_lat: float, to_lng: float, to_lat: float, mode: str) -> str:
        return f"{from_lng:.4f},{from_lat:.4f}→{to_lng:.4f},{to_lat:.4f}#{mode}"

    async def route_get(self, from_lng: float, from_lat: float,
                        to_lng: float, to_lat: float, mode: str) -> dict | None:
        key = self.route_key(from_lng, from_lat, to_lng, to_lat, mode)
        return self._route.get(key)

    async def route_set(self, from_lng: float, from_lat: float,
                        to_lng: float, to_lat: float, mode: str, route: dict):
        key = self.route_key(from_lng, from_lat, to_lng, to_lat, mode)
        self._route[key] = route
        self._hits["route_set"] = self._hits.get("route_set", 0) + 1

    async def route(self, from_lng: float, from_lat: float,
                    to_lng: float, to_lat: float, mode: str = "transit") -> dict | None:
        """带缓存的路线查询"""
        cached = await self.route_get(from_lng, from_lat, to_lng, to_lat, mode)
        if cached is not None:
            self._hits["route_hit"] = self._hits.get("route_hit", 0) + 1
            return cached

        try:
            from app.services.map.amap import amap_service
            origin = f"{from_lng},{from_lat}"
            destination = f"{to_lng},{to_lat}"
            route = await amap_service.route_planning(origin, destination, mode)
            if route:
                await self.route_set(from_lng, from_lat, to_lng, to_lat, mode, route)
            return route
        except Exception:
            return None

    # ========== Embedding 缓存 ==========

    async def embed(self, query: str) -> list[float]:
        """带缓存的 Embedding"""
        if query in self._embedding:
            self._hits["embed_hit"] = self._hits.get("embed_hit", 0) + 1
            return self._embedding[query]

        from app.services.vector.embedding import embedding_service
        vec = await embedding_service.embed_query(query)
        self._embedding[query] = vec
        self._hits["embed_set"] = self._hits.get("embed_set", 0) + 1
        return vec

    # ========== 统计 ==========

    def stats(self) -> dict:
        """返回缓存命中统计"""
        total_saved = (
            self._hits.get("rag_hit", 0)
            + self._hits.get("geocode_hit", 0)
            + self._hits.get("route_hit", 0)
            + self._hits.get("embed_hit", 0)
        )
        return {
            "total_cached_queries": len(self._rag) + len(self._geocode) + len(self._route),
            "cache_hits": total_saved,
            "breakdown": dict(self._hits),
        }
