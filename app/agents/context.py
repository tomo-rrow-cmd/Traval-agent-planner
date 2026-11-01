"""
全局上下文 - 在多智能体间共享的规划状态

PlanContext 是唯一共享状态载体，所有字段有明确的 owner Agent。
每次写入必须增加版本和记录变更，便于回溯和恢复。

参考：.agent/architecture.md §5
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


@dataclass
class ContextChangeLog:
    """单次上下文变更记录"""

    version: int
    field_name: str
    agent_name: str          # 发起变更的 Agent
    timestamp: str           # ISO 8601
    summary: str             # 变更简述


@dataclass
class PlanContext:
    """
    旅行规划全局上下文。

    字段所有权（每个 Agent 只能写入自己负责的字段）：
        weather_data      → WeatherAgent
        attractions       → AttractionAgent
        restaurants       → FoodAgent
        hotels            → HotelAgent
        traffic_plan      → TrafficAgent
        daily_itinerary   → RouteOptimizerAgent
        total_cost        → BudgetAgent
        souvenirs         → SouvenirAgent
    """

    # ---- 用户输入（UserInteractionAgent 写入） ----
    user_id: str = ""
    destination: str = ""
    start_date: date | None = None
    end_date: date | None = None
    budget: float = 0.0
    travelers: int = 1
    preferences: list[str] = field(default_factory=list)

    # ---- 用户偏好（UserInteractionAgent 写入） ----
    cuisine_preferences: list[str] = field(default_factory=list)
    hotel_star_min: int = 3
    preferred_transport: str = "地铁"
    pace: str = "适中"

    # ---- Agent 输出（各 Agent 逐步填充） ----
    weather_data: list[dict] = field(default_factory=list)
    attractions: list[dict] = field(default_factory=list)
    restaurants: list[dict] = field(default_factory=list)
    hotels: list[dict] = field(default_factory=list)
    traffic_plan: dict[str, Any] = field(default_factory=dict)
    daily_itinerary: list[dict] = field(default_factory=list)
    total_cost: float = 0.0
    souvenirs: list[dict] = field(default_factory=list)

    # ---- 元信息 ----
    current_stage: str = "init"
    errors: list[str] = field(default_factory=list)

    # ---- 版本追踪（每次写入上下文时递增） ----
    context_version: int = 0
    change_log: list[ContextChangeLog] = field(default_factory=list)

    # ---- 写入方法 ----

    def write(
        self,
        field_name: str,
        value: Any,
        agent_name: str,
        summary: str = "",
    ) -> None:
        """
        安全写入上下文字段。

        自动递增版本号并记录变更日志。
        禁止 Agent 写入不属于自己的字段（调用方自行遵守）。

        参考：.agent/architecture.md §5
        """
        if not hasattr(self, field_name):
            raise AttributeError(f"PlanContext 不存在字段 '{field_name}'")

        setattr(self, field_name, value)
        self.context_version += 1

        self.change_log.append(ContextChangeLog(
            version=self.context_version,
            field_name=field_name,
            agent_name=agent_name,
            timestamp=datetime.utcnow().isoformat(),
            summary=summary or f"{agent_name} 更新了 {field_name}",
        ))

        # 保留最近 100 条变更记录，避免无限增长
        if len(self.change_log) > 100:
            self.change_log = self.change_log[-100:]

    def get_version(self) -> int:
        """获取当前上下文版本号"""
        return self.context_version

    def get_owner_agent(self, field_name: str) -> str | None:
        """查询字段的所有者 Agent（用于冲突检测）"""
        ownership = {
            "weather_data": "WeatherAgent",
            "attractions": "AttractionAgent",
            "restaurants": "FoodAgent",
            "hotels": "HotelAgent",
            "traffic_plan": "TrafficAgent",
            "daily_itinerary": "RouteOptimizerAgent",
            "total_cost": "BudgetAgent",
            "souvenirs": "SouvenirAgent",
        }
        return ownership.get(field_name)

    # ---- 工具方法 ----

    def to_dict(self) -> dict[str, Any]:
        """转为字典供 Agent 使用"""
        return {
            "user_id": self.user_id,
            "destination": self.destination,
            "start_date": str(self.start_date) if self.start_date else None,
            "end_date": str(self.end_date) if self.end_date else None,
            "budget": self.budget,
            "travelers": self.travelers,
            "preferences": self.preferences,
            "weather_data": self.weather_data,
            "attractions": self.attractions,
            "restaurants": self.restaurants,
            "hotels": self.hotels,
            "traffic_plan": self.traffic_plan,
            "daily_itinerary": self.daily_itinerary,
            "total_cost": self.total_cost,
            "souvenirs": self.souvenirs,
            "context_version": self.context_version,
        }

    def add_error(self, error: str):
        """记录错误"""
        self.errors.append(error)

    def update_stage(self, stage: str):
        """更新当前阶段"""
        self.current_stage = stage
