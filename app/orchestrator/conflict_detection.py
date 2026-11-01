"""
冲突检测模块 — 检测规划方案中的时间、位置、预算、营业时间冲突

中央协调器核心职责之一，参考：.agent/architecture.md §4
"""

from datetime import date, datetime, time
from typing import Any

from app.services.map.geocode import haversine_distance


class ConflictDetector:
    """
    冲突检测器。

    在 Agent 各自生成结果后、最终方案整合前，检测以下冲突类型：
    - 时间冲突：同一时段安排了多个无法同时到达的地点
    - 位置冲突：连续地点之间距超出合理范围
    - 预算冲突：累计费用超出总预算
    - 营业时间冲突：到达时间不在营业时间段内
    """

    MAX_WALKING_DISTANCE_KM = 5.0  # 两个相邻景点间最大步行距离 (km)
    MAX_DAILY_ATTRACTIONS = 5       # 单日最多景点数

    def detect_all(
        self,
        daily_itinerary: list[dict[str, Any]],
        total_budget: float,
        buffer_minutes: int = 30,
    ) -> list[dict[str, Any]]:
        """
        对整份行程执行全部冲突检测。

        Args:
            daily_itinerary: 每日行程列表
            total_budget: 总预算
            buffer_minutes: 地点间最小缓冲时间（分钟）

        Returns:
            冲突列表，每个冲突包含 type / severity / message / suggestion
        """
        conflicts: list[dict[str, Any]] = []

        for day_plan in daily_itinerary:
            conflicts.extend(
                self._detect_time_conflicts(day_plan, buffer_minutes)
            )
            conflicts.extend(
                self._detect_location_conflicts(day_plan)
            )
            conflicts.extend(
                self._detect_business_hours_conflicts(day_plan)
            )

        conflicts.extend(
            self._detect_budget_conflicts(daily_itinerary, total_budget)
        )

        return conflicts

    # ---- 时间冲突检测 ----

    def _detect_time_conflicts(
        self,
        day_plan: dict[str, Any],
        buffer_minutes: int,
    ) -> list[dict[str, Any]]:
        """
        检测同一日内地点间的时间冲突。

        规则：两个地点之间的交通时间 + buffer > 可用时间间隔 → 冲突。
        """
        conflicts: list[dict[str, Any]] = []
        stops = day_plan.get("attractions", [])

        for i in range(len(stops) - 1):
            curr = stops[i]
            next_stop = stops[i + 1]

            # 如果两个地点都有坐标，计算距离和交通时间
            curr_lat = curr.get("latitude")
            curr_lon = curr.get("longitude")
            next_lat = next_stop.get("latitude")
            next_lon = next_stop.get("longitude")

            if all([curr_lat, curr_lon, next_lat, next_lon]):
                distance = haversine_distance(curr_lat, curr_lon, next_lat, next_lon)
                from app.services.map.geocode import estimate_travel_time

                travel_time = estimate_travel_time(distance, "transit")

                curr_duration = curr.get("recommended_duration", 2) * 60  # 转为分钟

                if travel_time + buffer_minutes > 120:  # 超过 2 小时交通时间
                    conflicts.append({
                        "type": "time",
                        "severity": "warning",
                        "location": f"{curr.get('name', '')} → {next_stop.get('name', '')}",
                        "message": (
                            f"两地之间交通时间约 {travel_time:.0f} 分钟（距离 {distance:.1f} km），"
                            f"建议调整为同区域景点或预留充足时间"
                        ),
                        "suggestion": "考虑将两地安排在不同日期，或选择更近的替代景点",
                        "distance_km": round(distance, 1),
                        "travel_time_min": round(travel_time),
                    })

        return conflicts

    # ---- 位置冲突检测 ----

    def _detect_location_conflicts(
        self,
        day_plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        检测同一日景点数量是否合理、位置是否过于分散。
        """
        conflicts: list[dict[str, Any]] = []
        stops = day_plan.get("attractions", [])

        if len(stops) > self.MAX_DAILY_ATTRACTIONS:
            conflicts.append({
                "type": "location",
                "severity": "warning",
                "day": day_plan.get("day"),
                "message": (
                    f"当日安排了 {len(stops)} 个景点，超过建议上限 "
                    f"{self.MAX_DAILY_ATTRACTIONS} 个，可能导致行程过赶"
                ),
                "suggestion": "减少景点数量或延长旅行天数",
            })

        # 检查是否有同一天景点分散在城市不同方向
        coordinates = []
        for s in stops:
            lat, lon = s.get("latitude"), s.get("longitude")
            if lat and lon:
                coordinates.append((lat, lon, s.get("name", "")))

        for i in range(len(coordinates)):
            for j in range(i + 1, len(coordinates)):
                dist = haversine_distance(
                    coordinates[i][0], coordinates[i][1],
                    coordinates[j][0], coordinates[j][1],
                )
                if dist > 30:
                    conflicts.append({
                        "type": "location",
                        "severity": "error",
                        "location": f"{coordinates[i][2]} ↔ {coordinates[j][2]}",
                        "message": f"两景点直线距离 {dist:.1f} km，同一天游览不现实",
                        "suggestion": "安排在不同日期，或替换其中一个景点",
                        "distance_km": round(dist, 1),
                    })

        return conflicts

    # ---- 预算冲突检测 ----

    def _detect_budget_conflicts(
        self,
        daily_itinerary: list[dict[str, Any]],
        total_budget: float,
    ) -> list[dict[str, Any]]:
        """
        检测累计费用是否超出总预算。
        """
        conflicts: list[dict[str, Any]] = []

        estimated_total = 0.0
        for day_plan in daily_itinerary:
            for key in ("attractions", "restaurants", "hotels"):
                for item in day_plan.get(key, []):
                    price = (
                        item.get("price", 0)
                        or item.get("avg_price", 0)
                        or item.get("price_per_night", 0)
                        or 0
                    )
                    estimated_total += float(price)

        if estimated_total > total_budget:
            over_pct = (estimated_total - total_budget) / total_budget * 100
            conflicts.append({
                "type": "budget",
                "severity": "error",
                "message": (
                    f"预估总费用 ¥{estimated_total:.0f} 超出预算 "
                    f"¥{total_budget:.0f}（超支 {over_pct:.0f}%）"
                ),
                "suggestion": "降低住宿星级、选择免费景点、或调整餐饮预算",
                "estimated_total": round(estimated_total, 2),
                "budget": total_budget,
                "over_pct": round(over_pct, 1),
            })
        elif estimated_total > total_budget * 0.8:
            conflicts.append({
                "type": "budget",
                "severity": "warning",
                "message": (
                    f"预估总费用 ¥{estimated_total:.0f} 已达预算 "
                    f"¥{total_budget:.0f} 的 {estimated_total/total_budget*100:.0f}%"
                ),
                "suggestion": "预算已较紧，预留一些弹性空间",
                "estimated_total": round(estimated_total, 2),
                "budget": total_budget,
            })

        return conflicts

    # ---- 营业时间冲突检测 ----

    def _detect_business_hours_conflicts(
        self,
        day_plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        检测行程时间是否在景点/餐厅的营业时间范围内。

        V1.0 先做占位检测：如果景点标注了营业时间但行程中未填写到达时间 → 提示。
        """
        conflicts: list[dict[str, Any]] = []
        stops = day_plan.get("attractions", []) + day_plan.get("restaurants", [])

        for stop in stops:
            opening_hours = stop.get("opening_hours", "")
            arrival_time_str = stop.get("arrival_time", "")

            if opening_hours and not arrival_time_str:
                conflicts.append({
                    "type": "business_hours",
                    "severity": "info",
                    "location": stop.get("name", ""),
                    "message": f"营业时间 {opening_hours}，但未填写计划到达时间",
                    "suggestion": "建议确认到达时间在营业范围内",
                })

        return conflicts


# 全局冲突检测器
conflict_detector = ConflictDetector()
