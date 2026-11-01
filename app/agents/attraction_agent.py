"""
景点规划智能体 — 工具调用版

流程：
    1. 注册 search_attractions 工具
    2. DeepSeek 决定是否调用工具
    3. 工具执行 → 去 Chroma RAG/PostgreSQL 拿真实数据
    4. 数据回传 → DeepSeek 排序推荐
"""

import json
import re
from typing import Any

from app.agents.base import BaseAgent


class AttractionAgent(BaseAgent):
    """景点规划智能体 — 真实 Function Calling"""

    name = "attraction"
    description = "工具调用 → RAG 搜索真实景点 → LLM 排序推荐"

    MAX_CANDIDATES = 25

    def __init__(self, llm):
        super().__init__(llm)
        self.register_tools_from_registry(["search_attractions"])

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        destination = input_data.get("destination", "")
        days = int(input_data.get("days", 1))
        preferences = input_data.get("preferences", [])
        pace = input_data.get("pace", "适中")
        weather_impact = input_data.get("weather_impact", [])
        pref_text = "、".join(preferences) if preferences else "热门景点"
        pace_map = {"紧凑": "4-5个", "适中": "3-4个", "轻松": "2-3个"}
        daily_count = pace_map.get(pace, "3-4个")

        # ---- 构建 prompt，让 DeepSeek 决定是否调工具 ----
        system_msg = f"""你是{destination}景点规划师。你有工具 search_attractions 可以搜索真实景点数据。

用户需求：玩{days}天，偏好{pref_text}，节奏{pace}（每天{daily_count}个景点）。

步骤：
1. 先调用 search_attractions 获取{destination}的真实景点数据
2. 根据返回的数据，按评分和相关性筛选
3. 分配每天{daily_count}个景点，同一天的位置尽量相邻
4. 每个景点写推荐理由

必须调用 search_attractions 获取真实数据！不要凭空编造景点。"""

        # ---- 先 RAG 搜索拿坐标数据 ----
        candidates = await self._fallback_search(destination, pref_text)

        # ---- 城市无数据 → 高德实时搜索（轻量，不写库） ----
        if len(candidates) < 3:
            print(f"  [Agent] {destination} 数据不足({len(candidates)}条)，高德实时搜索...")
            try:
                from app.services.third_party.poi_live import live_search_attractions
                live = await live_search_attractions(destination, limit=15)
                if live:
                    candidates = live
                    print(f"  [Agent] 高德实时: {len(candidates)} 条")
            except Exception as e:
                print(f"  [Agent] 高德实时搜索失败: {e}")

        # ---- LLM 规划（带坐标提示） ----
        daily_plan = await self._llm_plan(candidates, destination, days, preferences, pace, weather_impact)

        # ---- 候选名称索引（精确 + 规范化 + 模糊） ----
        candidate_map = {}
        candidate_names = []
        for candidate in candidates:
            name = candidate.get("name", "")
            if name:
                candidate_map[name] = candidate
                candidate_map[_name_key(name)] = candidate
                candidate_names.append(name)

        def _fuzzy_match(attr_name: str) -> dict | None:
            """仅在唯一候选命中时使用双向子串匹配。"""
            nk = _name_key(attr_name)
            matches = []
            for cn in candidate_names:
                cnk = _name_key(cn)
                if cnk and nk and (cnk in nk or nk in cnk):
                    matches.append(candidate_map[cn])
            return matches[0] if len(matches) == 1 else None

        missing_coords = []
        matched = 0
        for day in daily_plan:
            for attraction in day.get("attractions", []):
                candidate = candidate_map.get(attraction.get("name", ""))
                candidate = candidate or candidate_map.get(_name_key(attraction.get("name", "")))
                if not candidate:
                    candidate = _fuzzy_match(attraction.get("name", ""))
                if candidate:
                    matched += 1
                    for field in (
                        "poi_id", "source", "source_poi_id", "rating", "price",
                        "latitude", "longitude", "address",
                        "category", "tags",
                    ):
                        val = candidate.get(field)
                        if val is not None:
                            attraction[field] = val
                attraction.setdefault("price", 0)
                if not (attraction.get("latitude") and attraction.get("longitude")):
                    missing_coords.append(attraction.get("name", ""))
        if missing_coords:
            print(f"  [Agent] 缺少坐标: {', '.join(missing_coords[:5])}")
        total_attrs = sum(len(d.get("attractions", [])) for d in daily_plan)
        print(f"  [Agent] 候选匹配: {matched}/{total_attrs} ({matched*100//max(total_attrs,1)}%)")

        return self._validate({
            "attractions": candidates[:self.MAX_CANDIDATES],
            "daily_plan": daily_plan,
            "candidate_count": len(candidates),
        })

    async def _fallback_search(self, city: str, keywords: str) -> list[dict]:
        """从带完整 POI 元数据的 RAG 索引检索候选。"""
        from app.services.vector.rag import rag_search

        candidates = []
        try:
            results = await rag_search(
                "attractions",
                f"在{city}，推荐{keywords}，评分高人气旺的必去景点",
                where={"city": city},
                final_k=self.MAX_CANDIDATES,
                preferences=keywords.split("、") if keywords else None,
            )

            for item in results:
                name = item.get("name", item.get("id", ""))
                candidate = {
                    "poi_id": item.get("id", ""),
                    "source": item.get("source", ""),
                    "source_poi_id": item.get("source_poi_id", ""),
                    "name": name,
                    "rating": item.get("rating", 0),
                    "price": item.get("price", 0),
                    "category": item.get("category", ""),
                    "tags": item.get("tags", ""),
                    "address": item.get("address", ""),
                    "latitude": item.get("latitude") or None,
                    "longitude": item.get("longitude") or None,
                    "relevance": item.get("relevance", 0),
                }
                if item.get("rerank_score") is not None:
                    candidate["rerank_score"] = item["rerank_score"]
                candidates.append(candidate)
        except Exception as e:
            print(f"  [Attraction RAG] 失败: {e}")
        return candidates

    async def _llm_plan(self, candidates: list, dest: str, days: int,
                         prefs: list, pace: str,
                         weather_impact: list[dict] | None = None) -> list[dict]:
        weather_impact = weather_impact or []
        lines = []
        for i, c in enumerate(candidates[:self.MAX_CANDIDATES]):
            lat = f"{c.get('latitude', 0):.4f}" if c.get('latitude') else "?"
            lng = f"{c.get('longitude', 0):.4f}" if c.get('longitude') else "?"
            lines.append(f"{i+1}. {c['name']} | 评分:{c.get('rating','?')} | ¥{c.get('price',0):.0f} "
                         f"| 坐标:({lat},{lng}) | {c.get('tags','')}")

        # Build per-day weather summary
        weather_lines: list[str] = []
        for wi in weather_impact:
            suit = wi.get("outdoor_suitability", 1.0)
            label = (
                "【不适宜户外】优先室内景点" if suit < 0.3
                else "【较不适合户外】尽量室内景点" if suit < 0.5
                else "【需注意】做好防护" if suit < 0.7
                else "【适宜户外】"
            )
            weather_lines.append(
                f"第{wi['day_of_trip']}天 ({wi['date']}): {wi['dayweather']}, "
                f"{wi['daytemp']}°C, 户外适宜度 {suit:.0%}, "
                f"风力 {wi['daypower']}级 {label}"
            )

        pace_map = {"紧凑": "4-5个", "适中": "3-4个", "轻松": "2-3个"}
        weather_section = f"\n天气预报：\n{chr(10).join(weather_lines)}\n" if weather_lines else ""
        prompt = f"""{dest}{days}天，偏好{'、'.join(prefs) if prefs else '热门'}，每天{pace_map.get(pace, '3-4个')}景点。{weather_section}
候选（含真实经纬度，只能从中选！）：
{chr(10).join(lines)}

严格要求：
1. 只能从上述候选列表中选景点，不要编造任何不在列表中的景点！
2. 景点名必须原样复制，不要改名、不要加备注
3. 保留坐标(latitude,longitude)和门票价格(price)，写推荐理由
4. tags 字段从候选列表原样复制
5. JSON：
{{"daily_plan":[{{"day":1,"attractions":[{{"name":"","reason":"","duration_hours":2.5,"price":0,"latitude":39.9,"longitude":116.4,"tags":""}}]}}]}}"""

        try:
            resp = await self.call_llm([{"role": "user", "content": prompt}], temperature=0.7)
            return self._parse_plan(resp, days, candidates, weather_impact)
        except Exception:
            return self._fallback_plan(candidates, days, weather_impact)

    def _parse_plan(self, text: str, days: int, candidates: list,
                     weather_impact: list[dict] | None = None) -> list[dict]:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text) or re.search(r"\{[\s\S]*\"daily_plan\"[\s\S]*\}", text)
        json_str = m.group(1) if m and m.lastindex else text
        if m and not m.lastindex:
            json_str = m.group(0)
        try:
            plan = json.loads(json_str).get("daily_plan", [])
            if plan:
                return plan
        except Exception:
            pass
        return self._fallback_plan(candidates, days, weather_impact)

    def _fallback_plan(self, candidates: list, days: int,
                        weather_impact: list[dict] | None = None) -> list[dict]:
        weather_impact = weather_impact or []

        # Build per-day outdoor penalty from weather_impact
        outdoor_keywords = [
            "自然风光", "山水", "户外", "登山", "公园", "海滩", "园林", "古镇",
            "滑雪", "游乐园", "漂流", "栈道", "峡谷", "瀑布", "草原", "湿地",
            "森林公园", "山峰", "湖泊", "海滨", "沙漠",
        ]
        indoor_keywords = [
            "博物馆", "美术馆", "科技馆", "购物中心", "商场", "剧院", "水族馆",
            "温泉", "SPA", "纪念馆", "规划馆", "图书馆", "文化宫", "展览",
        ]

        def _weather_aware_score(c: dict) -> float:
            base = _rank_score(c)
            tags_str = str(c.get("tags", ""))
            is_outdoor = any(kw in tags_str for kw in outdoor_keywords)
            is_indoor = any(kw in tags_str for kw in indoor_keywords)
            if is_outdoor and not is_indoor and weather_impact:
                # Apply worst-day penalty across all days (approximate)
                avg_penalty = sum(
                    wi.get("outdoor_suitability", 1.0) for wi in weather_impact
                ) / max(len(weather_impact), 1)
                return base * avg_penalty
            return base

        sorted_c = sorted(candidates, key=_weather_aware_score, reverse=True)
        per_day = max(2, len(sorted_c) // days) if sorted_c else 0
        plan = []
        for d in range(days):
            chunk = sorted_c[d*per_day:(d+1)*per_day]
            plan.append({"day": d+1, "attractions": [
                 {"name": c["name"], "reason": f"评分 {c.get('rating', 0)}", "duration_hours": 2.0,
                  "poi_id": c.get("poi_id"), "source": c.get("source"),
                  "source_poi_id": c.get("source_poi_id"), "rating": c.get("rating", 0),
                  "price": c.get("price", 0),
                  "latitude": c.get("latitude"), "longitude": c.get("longitude"),
                  "address": c.get("address", ""),
                  "category": c.get("category", ""),
                  "tags": c.get("tags", "")}
                 for c in chunk
             ]})
        return plan

    def _validate(self, data: dict) -> dict:
        from app.schemas.agent_outputs import AttractionOutput
        return self.validate_output(data, AttractionOutput)


def _rank_score(candidate: dict) -> float:
    rerank_score = candidate.get("rerank_score")
    return rerank_score if rerank_score is not None else candidate.get("relevance", 0)


def _name_key(name: str) -> str:
    text = str(name or "").replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", text.split("(", 1)[0]).lower()
