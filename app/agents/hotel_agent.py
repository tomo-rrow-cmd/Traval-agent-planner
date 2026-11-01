"""
住宿推荐智能体 — 美团酒旅 Skill（真实价格+评分） + Chroma RAG 兜底
"""

import re
from typing import Any
from app.agents.base import BaseAgent
from app.services.vector.rag import rag_search


class HotelAgent(BaseAgent):
    """住宿推荐 — 美团优先"""

    name = "hotel"
    description = "美团 CLI 真实价格 → Chroma RAG 兜底 → LLM 推荐"

    def __init__(self, llm):
        super().__init__(llm)
        self.register_tools_from_registry(["meituan_travel", "search_hotels"])

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        destination = input_data.get("destination", "")
        days = int(input_data.get("days", 1))
        star_min = input_data.get("hotel_star_min", 3)
        budget = input_data.get("budget_per_night", 500)
        nights = max(days - 1, 0)

        meituan_text, meituan_hotels = await self._fetch_meituan(destination, star_min, budget)
        candidates = await self._fetch_rag_candidates(destination, star_min, budget)

        if meituan_hotels:
            return await self._build_meituan_response(meituan_hotels, meituan_text, candidates,
                                                       destination, nights, budget)

        return await self._build_fallback_response(candidates, destination, nights, budget,
                                                    meituan_text, meituan_hotels)

    # ---- 数据拉取 ----

    async def _fetch_meituan(self, destination: str, star_min: int, budget: float) -> tuple[str, list]:
        try:
            from app.services.third_party.meituan import meituan
            if meituan.available:
                q = f"推荐酒店，{star_min}星级以上，预算{budget}元以内，靠近市中心交通便利"
                result = await meituan.query(destination, q)
                if result.get("success"):
                    from app.services.third_party.meituan_parser import parse_hotels
                    return result["text"], parse_hotels(result["text"])
        except Exception as e:
            print(f"  [美团] {e}")
        return "", []

    async def _fetch_rag_candidates(self, destination: str, star_min: int, budget: float) -> list:
        try:
            return await rag_search(
                "hotels", f"{destination} {star_min}星酒店 ¥{budget}以内",
                where={"city": destination}, final_k=10, max_price=budget,
            )
        except Exception as e:
            print(f"  [Hotel RAG] 失败: {e}")
            return []

    async def _enrich_coordinates(self, name: str, city: str, local: dict) -> tuple:
        """优先用 RAG 候选坐标，缺失则 Amap 反查"""
        lat = local.get("latitude") or None
        lng = local.get("longitude") or None
        if lat and lng:
            return lat, lng
        try:
            from app.services.map.amap import AmapService
            pois = await AmapService().search_poi(keywords=name, city=city, offset=1)
            if pois and pois[0].get("location"):
                parts = pois[0]["location"].split(",")
                return float(parts[1]), float(parts[0])
        except Exception:
            pass
        return None, None

    # ---- 响应组装 ----

    async def _build_meituan_response(self, meituan_hotels: list, meituan_text: str,
                                       candidates: list, destination: str,
                                       nights: int, budget: float) -> dict:
        local_by_name = {_name_key(c.get("name", "")): c for c in candidates if c.get("name")}
        recommendations = []

        for h in meituan_hotels[:2]:
            price = h.get("price", 0) or 0
            price_verified = price > 10
            local = local_by_name.get(_name_key(h.get("name", "")), {})
            lat, lng = await self._enrich_coordinates(h.get("name", ""), destination, local)

            reason = h.get("reason") or f"美团评分 {h.get('rating', 0)}"
            if not price_verified:
                reason += "（价格待确认）"

            recommendations.append({
                "name": h.get("name", ""), "reason": reason,
                "price_per_night": price if price_verified else budget,
                "raw_price": price, "price_verified": price_verified,
                "price_source": "meituan", "estimated": not price_verified,
                "nights": nights, "total": (price if price_verified else budget) * nights,
                "rating": h.get("rating", 0), "link": h.get("link", ""),
                "image": h.get("image", ""), "tags": h.get("tags", []),
                "latitude": lat, "longitude": lng,
                "poi_id": local.get("id"), "source": local.get("source") or "meituan",
                "source_poi_id": local.get("source_poi_id"),
                "address": local.get("address", ""),
                "coordinates_available": bool(lat and lng),
            })

        return {
            "hotels": meituan_hotels, "meituan_raw": meituan_text,
            "meituan_hotels": meituan_hotels,
            "hotel_plan": {
                "recommendations": recommendations,
                "summary": "数据来自美团酒旅，价格为实时解析结果",
            },
            "source": "meituan",
        }

    async def _build_fallback_response(self, candidates: list, destination: str,
                                        nights: int, budget: float,
                                        meituan_text: str, meituan_hotels: list) -> dict:
        if len(candidates) < 3:
            print(f"  [Hotel] {destination} 数据不足，高德实时搜索...")
            try:
                from app.services.third_party.poi_live import live_search_hotels
                live = await live_search_hotels(destination, limit=10)
                if live:
                    candidates = live
            except Exception as e:
                print(f"  [Hotel] 高德实时搜索失败: {e}")

        chroma_plan = {}
        try:
            chroma_plan = {
                "recommendations": [
                    {"name": c["name"], "reason": f"评分 {c.get('rating','N/A')}",
                     "price_per_night": c.get("price_per_night", 0) or budget,
                     "price_verified": False, "estimated": not bool(c.get("price_per_night", 0)),
                     "nights": nights, "total": (c.get("price_per_night", 0) or budget) * nights,
                     "rating": c.get("rating", 0),
                     "latitude": c.get("latitude") or None,
                     "longitude": c.get("longitude") or None,
                     "poi_id": c.get("id"), "source": c.get("source"),
                     "source_poi_id": c.get("source_poi_id"),
                     "address": c.get("address", ""),
                     "coordinates_available": bool(c.get("latitude") and c.get("longitude"))}
                    for c in candidates[:2]
                ],
                "summary": "数据来自高德 POI；缺失价格时使用每晚预算做估算"
            }
        except (KeyError, TypeError, ValueError) as e:
            print(f"  [Hotel] 候选格式错误: {e}")

        return {
            "hotels": candidates, "meituan_raw": meituan_text,
            "meituan_hotels": meituan_hotels,
            "hotel_plan": chroma_plan,
            "source": "meituan" if meituan_text else "amap",
        }


def _name_key(name: str) -> str:
    text = str(name or "").replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", text.split("(", 1)[0]).lower()
