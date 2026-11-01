"""
AdjustAgent — 动态调整

触发条件:
- 天气突变（暴雨/高温/大风）→ 户外景点换室内
- 时间漂移（签到迟到 >30min）→ 压缩后续行程
- 预算超支（已花 > 计划 120%）→ 降级建议
- 用户主动请求

复用 V1.0 Agent: AttractionAgent（搜索替代景点）、HotelAgent（降级酒店）
"""

from typing import Any

from app.agents.base import BaseAgent
from app.services.llm.base import BaseLLM


class AdjustAgent(BaseAgent):
    name = "adjust"
    description = "动态调整 — 天气/时间/预算 异常处理"

    def __init__(self, llm: BaseLLM):
        super().__init__(llm)

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """根据 trigger_type 分发"""
        trigger = input_data.get("trigger_type", "")
        if trigger == "weather":
            return await self.handle_weather(input_data)
        elif trigger == "time_drift":
            return await self.handle_time_drift(input_data)
        elif trigger == "budget_alert":
            return await self.handle_budget_alert(input_data)
        elif trigger == "user_request":
            return await self.handle_user_request(input_data)
        return {"error": f"Unknown trigger: {trigger}"}

    # ========== 天气调整 ==========

    async def handle_weather(self, data: dict) -> dict:
        """
        天气影响分析:
        - 暴雨/大风 → 户外景点替换为室内博物馆/商场/餐厅
        - 高温 (>38°C) → 建议午后室内休息，调整游览顺序
        - 调用 AttractionAgent 搜索替代景点
        """
        affected_days = data.get("affected_days", [])
        weather_type = data.get("weather_type", "")  # 暴雨/高温/大风
        destination = data.get("destination", "")
        daily_plan = data.get("daily_plan", [])
        preferences = data.get("preferences", [])

        adjustments = []
        for day in affected_days:
            day_data = next((d for d in daily_plan if d.get("day") == day), None)
            if not day_data:
                continue

            affected_attrs = self._find_outdoor_attractions(day_data, weather_type)
            if not affected_attrs:
                continue

            # 搜索室内替代方案
            alternatives = await self._search_indoor_alternatives(
                destination, affected_attrs, preferences)

            adjustments.append({
                "day": day,
                "type": "weather",
                "weather": weather_type,
                "affected_attractions": affected_attrs,
                "alternatives": alternatives,
                "suggestion": self._weather_suggestion(weather_type, len(affected_attrs)),
            })

        original = self._extract_day_sections(daily_plan, affected_days)
        adjusted = self._apply_weather_changes(daily_plan, adjustments)

        return {
            "trigger_type": "weather",
            "trigger_detail": {"weather": weather_type, "affected_days": affected_days},
            "original_plan": original,
            "adjusted_plan": adjusted,
            "adjustments": adjustments,
            "reason": self._weather_reason(weather_type, adjustments),
            "requires_confirmation": True,
        }

    # ========== 时间漂移调整 ==========

    async def handle_time_drift(self, data: dict) -> dict:
        """
        时间漂移处理:
        - 上午迟到 → 删除低优先级景点 + 压缩停留时间
        - 策略: 保留高评分 → 砍低评分、压缩每站时间 → 餐时不变
        """
        current_day = data.get("current_day", 1)
        drift_min = data.get("drift_min", 0)  # 正=落后
        today_plan = data.get("today_plan", {})
        remaining_stops = data.get("remaining_stops", [])
        hotel_plan = data.get("hotel_plan", {})

        if drift_min <= 0:
            return {"trigger_type": "time_drift", "reason": "ahead or on time, no adjustment needed"}

        # 压缩策略
        adjusted_stops, removed = self._compress_stops(remaining_stops, drift_min)
        original = {"day": current_day, "stops": remaining_stops}
        adjusted = {"day": current_day, "stops": adjusted_stops}

        return {
            "trigger_type": "time_drift",
            "trigger_detail": {"drift_min": drift_min, "day": current_day},
            "original_plan": original,
            "adjusted_plan": adjusted,
            "removed_stops": removed,
            "reason": f"已落后{drift_min}分钟，建议压缩{len(removed)}个景点为自由活动或次日补上",
            "requires_confirmation": True,
        }

    # ========== 预算预警 ==========

    async def handle_budget_alert(self, data: dict) -> dict:
        """
        预算超支:
        - 推荐降级酒店档位
        - 餐饮降级建议
        - 提醒剩余预算逐项分配
        """
        spent = data.get("budget_spent", 0)
        total = data.get("budget_total", 1)
        over_pct = round((spent - total) / total * 100, 1) if total > 0 else 0
        remaining_days = data.get("remaining_days", 1)

        suggestions = []
        if remaining_days > 0:
            daily_remain = (total - spent) / remaining_days
            suggestions.append({
                "daily_budget_remaining": round(daily_remain, 2),
                "message": f"剩余每天可用 ¥{daily_remain:.0f}",
            })

        suggestions.append({"action": "降级餐饮", "detail": "晚餐选人均¥50以下的小吃/简餐"})
        suggestions.append({"action": "地铁替代打车", "detail": "市内交通用地铁，预计每天省¥30-50"})
        suggestions.append({"action": "免费景点优先", "detail": "公园/步行街/博物馆大多免费"})

        return {
            "trigger_type": "budget_alert",
            "trigger_detail": {"spent": spent, "total": total, "over_pct": over_pct},
            "suggestions": suggestions,
            "reason": f"已花 ¥{spent:.0f}/{total:.0f} ({over_pct}%)，剩余{remaining_days}天建议控制花费",
            "requires_confirmation": False,  # 预算提醒不需要确认
        }

    # ========== 用户主动调整 ==========

    async def handle_user_request(self, data: dict) -> dict:
        """
        用户主动请求: 换景点/换餐厅/加景点/删景点
        通过 LLM 理解意图并给出建议
        """
        request_text = data.get("request", "")
        daily_plan = data.get("daily_plan", [])
        destination = data.get("destination", "")

        prompt = f"""用户想调整行程: "{request_text}"
目的地: {destination}
当前行程: {self._summarize_plan(daily_plan)}
请分析用户意图，给出3条可行建议。每条50字以内。"""

        try:
            reply = await self.call_llm([{"role": "user", "content": prompt}], temperature=0.7)
        except Exception:
            reply = "收到调整请求，建议查看附近替代方案。"

        return {
            "trigger_type": "user_request",
            "trigger_detail": {"request": request_text},
            "reason": reply,
            "requires_confirmation": True,
        }

    # ================================================================
    #  Helpers
    # ================================================================

    OUTDOOR_TAGS = ["自然风光", "山水", "户外", "登山", "公园", "海滩", "园林", "古镇", "滑雪", "游乐园"]
    INDOOR_TAGS = ["博物馆", "美术馆", "科技馆", "购物中心", "商场", "剧院", "水族馆", "温泉", "SPA"]

    def _find_outdoor_attractions(self, day_data: dict, weather: str) -> list[dict]:
        """识别受天气影响的户外景点"""
        if weather not in ("暴雨", "大风", "高温"):
            return []
        affected = []
        for a in day_data.get("attractions", []):
            tags = a.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(";")]
            if any(ot in (tags or []) for ot in self.OUTDOOR_TAGS) or \
               any(ot in (a.get("category", "")) for ot in ["公园", "自然风光"]):
                affected.append(a)
        return affected

    async def _search_indoor_alternatives(self, city: str, affected: list[dict],
                                          preferences: list[str]) -> list[dict]:
        """搜索室内替代景点"""
        try:
            from app.agents.attraction_agent import AttractionAgent
            agent = AttractionAgent(self.llm)
            result = await agent.run({
                "destination": city,
                "days": 1,
                "preferences": (preferences or []) + ["室内", "博物馆", "休闲"],
                "pace": "relaxed",
            })
            candidates = result.get("attractions", [])
            # 过滤：排除与原景点重名的，优先室内类
            affected_names = {a.get("name", "") for a in affected}
            indoor = [c for c in candidates
                      if c.get("name") not in affected_names
                      and any(t in str(c.get("tags", "")) for t in self.INDOOR_TAGS)]
            return indoor[:max(len(affected), 3)]
        except Exception:
            return [{"name": "当地博物馆", "reason": "室内替代，建议搜索"},]

    def _weather_suggestion(self, weather: str, count: int) -> str:
        if weather == "暴雨":
            return f"{count}个户外景点受暴雨影响，建议改为室内博物馆/商场/下午茶"
        elif weather == "高温":
            return f"{count}个户外景点建议上午游览，午后安排室内休息"
        elif weather == "大风":
            return f"{count}个景点受大风影响，建议替换为室内活动"
        return ""

    def _weather_reason(self, weather: str, adjustments: list) -> str:
        total = sum(len(a.get("affected_attractions", [])) for a in adjustments)
        return f"{weather}预警：{total}个户外景点受影响，建议更换为室内方案"

    def _compress_stops(self, stops: list[dict], drift_min: int) -> tuple[list[dict], list[dict]]:
        """压缩行程：缩停留时间 + 砍低评分"""
        if not stops:
            return stops, []

        # 需要省出 drift_min 分钟
        target_save = drift_min
        saved = 0
        adjusted = []
        removed = []

        for s in stops:
            if saved >= target_save:
                adjusted.append(s)
                continue

            rating = s.get("rating", 3.0)
            duration = s.get("duration_h", s.get("duration_hours", 2))

            # 低评分（<3.5）且省时间多的优先砍
            if rating < 3.5 and duration >= 1 and s.get("type") != "restaurant":
                saved += int(duration * 60)
                removed.append({**s, "removed_reason": "low_rating"})
            else:
                # 压缩停留时间
                new_duration = max(0.5, duration * 0.7)
                saved += int((duration - new_duration) * 60)
                adjusted.append({**s, "duration_hours": round(new_duration, 1),
                                 "compressed": True})

        return adjusted, removed

    def _extract_day_sections(self, daily_plan: list, days: list) -> list:
        return [d for d in daily_plan if d.get("day") in days]

    def _apply_weather_changes(self, daily_plan: list, adjustments: list) -> list:
        """将室内替代方案并入 daily_plan"""
        result = [dict(d) for d in daily_plan]
        for adj in adjustments:
            day_data = next((d for d in result if d.get("day") == adj["day"]), None)
            if not day_data:
                continue
            affected_names = {a["name"] for a in adj.get("affected_attractions", [])}
            day_data["attractions"] = [
                a for a in day_data.get("attractions", [])
                if a.get("name") not in affected_names
            ]
            for alt in adj.get("alternatives", []):
                day_data.setdefault("attractions", []).append({
                    "name": alt.get("name", ""),
                    "reason": alt.get("reason", "天气调整替代"),
                    "is_alternative": True,
                    "tags": alt.get("tags", []),
                })
        return result

    def _summarize_plan(self, daily_plan: list) -> str:
        lines = []
        for d in daily_plan or []:
            names = [a.get("name", "") for a in d.get("attractions", [])]
            lines.append(f"Day{d.get('day')}: {', '.join(names[:5])}")
        return "; ".join(lines)
