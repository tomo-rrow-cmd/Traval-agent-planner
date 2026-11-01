"""
路线优化智能体 — 2-opt 局部搜索 + LLM 调整建议

D-004 决策：路线优化使用确定性算法，LLM 只做建议。
"""

from typing import Any

from app.agents.base import BaseAgent
from app.services.map.geocode import haversine_distance


class RouteOptimizerAgent(BaseAgent):
    """路线优化智能体 — 2-opt 算法版"""

    name = "route_optimizer"
    description = "2-opt 局部搜索优化每日游览顺序 + DeepSeek 出行建议"

    async def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        daily_itinerary = input_data.get("daily_itinerary", [])
        preferred_transport = input_data.get("preferred_transport", "地铁")

        optimized = []
        total_saved = 0.0

        for day_plan in daily_itinerary:
            attrs = day_plan.get("attractions", [])
            if len(attrs) <= 2:
                optimized.append(day_plan)
                continue

            # 记录原始顺序
            original_names = [a["name"] for a in attrs]

            # 2-opt 局部搜索优化
            reordered, opt_dist = _two_opt(attrs)
            orig_dist = _path_distance(attrs)

            saved = orig_dist - opt_dist
            total_saved += saved

            optimized.append({
                "day": day_plan.get("day", 1),
                "attractions": reordered,
                "original_order": original_names,
                "optimized_order": [a["name"] for a in reordered],
                "distance_before_km": round(orig_dist, 1),
                "distance_after_km": round(opt_dist, 1),
                "saved_km": round(saved, 1),
                "saved_time_min": round(max(0, saved) / 20 * 60, 0),
            })

        suggestions = await self._llm_suggestions(optimized)

        return {
            "optimized_itinerary": optimized,
            "total_saved_distance_km": round(total_saved, 1),
            "suggestions": suggestions,
        }

    async def _llm_suggestions(self, optimized: list) -> str:
        """DeepSeek 生成路线优化效果的文字说明"""
        lines = []
        for d in optimized:
            if d.get("saved_km", 0) > 0.5:
                lines.append(f"第{d['day']}天: 优化后 {' → '.join(d['optimized_order'])}，节省 {d['saved_km']}km")
            else:
                lines.append(f"第{d['day']}天: 路线已是最优")

        prompt = f"""行程路线优化结果：
{chr(10).join(lines) if lines else '各天路线均已是最优顺序'}
用2-3句话总结优化效果和出行建议。简洁。"""

        try:
            return await self.call_llm([{"role": "user", "content": prompt}], temperature=0.5)
        except Exception:
            return ""


# ---- 2-opt 算法 ----

def _two_opt(attractions: list[dict]) -> tuple[list[dict], float]:
    """
    2-opt 局部搜索：反复交换两条边来缩短总路径。

    从贪心初始解开始，尝试所有可能的边交换，
    如果一次交换能减少总距离则接受，直到无法改进为止。
    """
    if len(attractions) <= 2:
        return list(attractions), _path_distance(attractions)

    # 贪心最近邻作为初始解
    route = _greedy_init(attractions)
    best_dist = _path_distance(route)
    improved = True
    n = len(route)

    while improved:
        improved = False
        for i in range(1, n - 1):
            for j in range(i + 1, n):
                # 反转 i..j 段（2-opt swap）
                new_route = route[:i] + route[i:j + 1][::-1] + route[j + 1:]
                new_dist = _path_distance(new_route)
                if new_dist < best_dist - 0.01:  # 显著改进才接受
                    route = new_route
                    best_dist = new_dist
                    improved = True

    return route, best_dist


def _greedy_init(attractions: list[dict]) -> list[dict]:
    """贪心最近邻初始解"""
    remaining = attractions.copy()
    route = [remaining.pop(0)]
    while remaining:
        last = route[-1]
        nearest_i = min(
            range(len(remaining)),
            key=lambda i: _dist(last, remaining[i]),
        )
        route.append(remaining.pop(nearest_i))
    return route


def _path_distance(attractions: list[dict]) -> float:
    """总路径距离（km）"""
    total = 0.0
    for i in range(len(attractions) - 1):
        total += _dist(attractions[i], attractions[i + 1])
    return total


def _dist(a: dict, b: dict) -> float:
    """两点间距离"""
    return haversine_distance(
        a.get("latitude") or 0, a.get("longitude") or 0,
        b.get("latitude") or 0, b.get("longitude") or 0,
    )
