"""
美食推荐智能体 — RAG 语义搜索 + LLM 排序推荐

逻辑和景点 Agent 一致：偏好 → embedding → Chroma 搜索 → DeepSeek 推荐
"""

import json
import re
from typing import Any

from app.agents.base import BaseAgent
from app.services.vector.rag import rag_search


class FoodAgent(BaseAgent):
    """美食推荐智能体 — RAG 语义搜索版"""

    name = "food"
    description = "BGE embedding → Chroma 语义搜索餐厅 → DeepSeek 推荐每日三餐"

    MAX_CANDIDATES = 25

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        destination = input_data.get("destination", "")
        days = int(input_data.get("days", 1))
        cuisine_prefs = input_data.get("cuisine_preferences", [])
        meal_budget = input_data.get("meal_budget", 100)
        daily_locations = input_data.get("daily_locations", [])  # 已有的景点行程

        # ---- 1. 语义搜索 ----
        pref_text = "、".join(cuisine_prefs) if cuisine_prefs else "当地特色美食 热门餐厅"
        query = f"在{destination}，{pref_text}，人均{meal_budget}元左右"

        candidates = await self._rag_search(query, destination)

        # ---- 2. 数据不够 → 自动拉取 ----
        if len(candidates) < 3:
            print(f"  [Food] {destination} 数据不足，自动拉取...")
            try:
                import asyncio as _aio
                proc = await _aio.create_subprocess_exec(
                    "python", "scripts/seed_poi.py", "--city", destination,
                    stdout=_aio.subprocess.PIPE, stderr=_aio.subprocess.PIPE,
                )
                await _aio.wait_for(proc.communicate(), timeout=180.0)
                candidates = await self._rag_search(query, destination)
            except Exception as e:
                print(f"  [Food] 拉取失败: {e}")

        if len(candidates) < 5:
            candidates += await self._db_fallback(destination)

        if not candidates:
            return {
                "restaurants": [], "meal_plan": [],
                "message": f"未找到 {destination} 餐厅数据，自动拉取也未获取到，请稍后重试",
            }

        # ---- 3. LLM 分配三餐 ----
        meal_plan = await self._llm_plan(candidates, destination, days, cuisine_prefs, meal_budget, daily_locations)
        _attach_candidate_data(meal_plan, candidates)

        # ---- 4. 补坐标（从 PostgreSQL） ----
        await self._enrich_coords(meal_plan, destination)

        return {
            "restaurants": candidates[:self.MAX_CANDIDATES],
            "meal_plan": meal_plan,
            "candidate_count": len(candidates),
        }

    async def _rag_search(self, query: str, city: str) -> list[dict]:
        """BGE-M3 embedding → Chroma Top-K → reranker"""
        try:
            results = await rag_search(
                "restaurants",
                query,
                where={"city": city},
                final_k=self.MAX_CANDIDATES,
                preferences=query.split("，"),
            )
            candidates = []
            for item in results:
                candidate = {
                    "name": item.get("name", item.get("id", "")),
                    "cuisine": item.get("cuisine", ""),
                    "rating": item.get("rating", 0),
                    "avg_price": item.get("avg_price", 0),
                    "tags": item.get("tags", ""),
                    "relevance": item.get("relevance", 0),
                    "poi_id": item.get("poi_id") or item.get("id"),
                    "source": item.get("source"),
                    "source_poi_id": item.get("source_poi_id"),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "address": item.get("address", ""),
                }
                if item.get("rerank_score") is not None:
                    candidate["rerank_score"] = item["rerank_score"]
                candidates.append(candidate)
            return candidates
        except Exception as e:
            print(f"  [Food RAG] 失败: {e}")
            return []

    async def _enrich_coords(self, meal_plan: list, city: str):
        """从 DB 补餐厅坐标，消除 TrafficAgent 的估算"""
        from app.db.session import async_session_factory
        from app.db.models.restaurant import Restaurant
        from sqlalchemy import select

        try:
            async with async_session_factory() as db:
                all_rests = (await db.execute(
                    select(Restaurant).where(Restaurant.city == city)
                )).scalars().all()
            coord_map = {}
            for r in all_rests:
                if r.latitude and r.longitude:
                    coords = (r.latitude, r.longitude, r.address or "")
                    coord_map[r.name] = coords
                    coord_map[_name_key(r.name)] = coords
            for day in meal_plan:
                for meal in day.get("meals", []):
                    if meal.get("latitude") is not None and meal.get("longitude") is not None:
                        continue
                    name = meal.get("restaurant", "")
                    coords = coord_map.get(name) or coord_map.get(_name_key(name))
                    if coords:
                        meal["latitude"], meal["longitude"], meal["address"] = coords
        except Exception as e:
            print(f"  [Food enrich] 失败: {e}")

    async def _db_fallback(self, city: str) -> list[dict]:
        """从 PostgreSQL 直接查询餐厅数据"""
        try:
            from app.db.session import async_session_factory
            from sqlalchemy import select
            from app.db.models.restaurant import Restaurant

            async with async_session_factory() as db:
                results = (await db.execute(
                    select(Restaurant).where(Restaurant.city == city, Restaurant.avg_price >= 0)
                )).scalars().all()
                return [
                    {"name": r.name, "cuisine": r.cuisine or "", "rating": r.rating or 0,
                     "avg_price": r.avg_price or 0, "tags": "", "relevance": 0,
                     "latitude": r.latitude, "longitude": r.longitude, "address": r.address or ""}
                    for r in results[:10]
                ]
        except Exception as e:
            print(f"  [Food DB] 失败: {e}")
            return []

    async def _llm_plan(self, candidates: list, destination: str, days: int,
                         prefs: list, budget: float, daily_locations: list) -> list[dict]:
        """DeepSeek 分配每日三餐"""
        lines = []
        for i, c in enumerate(candidates[:self.MAX_CANDIDATES], 1):
            lines.append(f"{i}. {c['name']} | 菜系:{c.get('cuisine','?')} | 评分:{c.get('rating','?')} | 人均¥{c.get('avg_price',0):.0f} | 标签:{c.get('tags','')}")

        pref_text = "、".join(prefs) if prefs else "各种口味"
        # 已有景点位置信息
        loc_hint = ""
        if daily_locations:
            loc_hint = f"\n已有每日行程景点：{json.dumps(daily_locations, ensure_ascii=False)[:500]}"

        prompt = f"""你是{destination}美食推荐专家。用户玩{days}天，偏好{pref_text}，人均餐标¥{budget}。
{loc_hint}

候选餐厅（按语义相关度排序）：
{chr(10).join(lines)}

严格要求：
1. 必须为每一天（day 1 到 day {days}）都推荐午餐和晚餐各1家
2. 每天2家不能重复，不同天可以重复使用最匹配的候选
3. 价格控制在人均¥{budget}以内
4. 每家写一句推荐理由

只返回 JSON（确保包含全部 {days} 天）：
{{"meal_plan":[
  {{"day":1,"meals":[
    {{"meal":"午餐","restaurant":"店名","reason":"理由","avg_price":50}},
    {{"meal":"晚餐","restaurant":"店名","reason":"理由","avg_price":80}}
  ]}},
  ...直到 day {days}
]}}"""

        try:
            response = await self.call_llm([{"role": "user", "content": prompt}], temperature=0.7)
            return json.loads(_extract_json(response)).get("meal_plan", [])
        except Exception as e:
            print(f"  [Food LLM] 失败: {e}")
            return _fallback_meals(candidates, days)


def _extract_json(text: str) -> str:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m: return m.group(1).strip()
    m = re.search(r"\{[\s\S]*\}", text)
    if m: return m.group(0).strip()
    return text.strip()


def _fallback_meals(candidates: list, days: int) -> list[dict]:
    sorted_cands = sorted(candidates, key=lambda x: (_rank_score(x), x.get("rating", 0)), reverse=True)
    plan = []
    for d in range(days):
        lunch = sorted_cands[d * 2] if d * 2 < len(sorted_cands) else None
        dinner = sorted_cands[d * 2 + 1] if d * 2 + 1 < len(sorted_cands) else None
        meals = []
        if lunch:
            meals.append({"meal": "午餐", "restaurant": lunch["name"], "reason": f"评分 {lunch.get('rating', 'N/A')}", "avg_price": lunch.get("avg_price", 0)})
        if dinner:
            meals.append({"meal": "晚餐", "restaurant": dinner["name"], "reason": f"评分 {dinner.get('rating', 'N/A')}", "avg_price": dinner.get("avg_price", 0)})
        plan.append({"day": d + 1, "meals": meals})
    return plan


def _attach_candidate_data(meal_plan: list[dict], candidates: list[dict]) -> None:
    candidate_map = {}
    for candidate in candidates:
        name = candidate.get("name", "")
        if name:
            candidate_map[name] = candidate
            candidate_map[_name_key(name)] = candidate

    for day in meal_plan:
        for meal in day.get("meals", []):
            restaurant = meal.get("restaurant", "")
            candidate = candidate_map.get(restaurant)
            candidate = candidate or candidate_map.get(_name_key(restaurant))
            if not candidate:
                continue
            for field in (
                "poi_id", "source", "source_poi_id", "rating", "avg_price",
                "latitude", "longitude", "address",
            ):
                meal[field] = candidate.get(field)


def _name_key(name: str) -> str:
    text = str(name or "").replace("（", "(").replace("）", ")")
    return re.sub(r"\s+", "", text.split("(", 1)[0]).lower()


def _rank_score(candidate: dict) -> float:
    rerank_score = candidate.get("rerank_score")
    return rerank_score if rerank_score is not None else candidate.get("relevance", 0)
