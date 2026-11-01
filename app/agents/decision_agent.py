"""
DecisionAgent — 两轮决策

Round1: 定稿景点+餐厅 (不含酒店)
Round2: 交通评估后选最优酒店
"""

from typing import Any

from app.agents.base import BaseAgent


class DecisionAgent(BaseAgent):
    name = "decision"
    description = "Round1定景点餐厅 + Round2选酒店"

    # ========== Round 1: 定稿景点+餐厅 ==========

    async def run_round1(self, input_data: dict[str, Any]) -> dict[str, Any]:
        daily_plan = input_data.get("daily_plan", [])
        meal_plan = input_data.get("meal_plan", [])

        finalized = []
        auto_trimmed = False
        for day in daily_plan:
            d = day.get("day", 1)
            md = next((m for m in meal_plan if m.get("day") == d), {"meals": []})
            attractions = day.get("attractions", [])
            if len(attractions) > 4:
                attractions = attractions[:4]
                auto_trimmed = True
            finalized.append({
                "day": d, "attractions": attractions,
                "meals": md.get("meals", []),
            })

        return {"stage": "finalized_r1", "daily_plan": finalized,
                "meal_plan": meal_plan, "decision_needed": False,
                "auto_trimmed": auto_trimmed}

    # ========== Round 2: 交通评分选酒店 ==========

    async def run_round2(self, input_data: dict[str, Any]) -> dict[str, Any]:
        hotel_plan = input_data.get("hotel_plan", {})
        daily_plan = input_data.get("daily_plan", [])
        destination = input_data.get("destination", "")

        recs = hotel_plan.get("recommendations", [])

        if recs:
            try:
                scored = bool(daily_plan)
                if scored:
                    from app.agents.traffic_agent import TrafficAgent
                    recs = await TrafficAgent.evaluate_hotels(
                        hotel_plan, daily_plan, destination)
                best = recs[0] if recs else None
                if best:
                    hotel_plan = {
                        **hotel_plan,
                        "recommendations": recs,
                        "selected": best["name"],
                        "selected_hotel": best,
                        "selection_reason": (
                            f"交通评分 {best['commute_score']} 最优"
                            if scored
                            else "缺少可评估日程，按候选顺序选择"
                        ),
                    }
            except Exception as exc:
                fallback = recs[0]
                hotel_plan = {
                    **hotel_plan,
                    "selected": fallback.get("name"),
                    "selected_hotel": fallback,
                    "selection_reason": "通勤评估失败，按候选顺序选择",
                    "selection_warning": str(exc),
                }

        return {"hotel_plan": hotel_plan, "decision_round2_done": True}

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """兼容旧调用。"""
        if input_data.get("hotel_plan") and input_data.get("traffic"):
            return await self.run_round2(input_data)
        round1 = await self.run_round1(input_data)
        return {**round1, "stage": "finalized"}
