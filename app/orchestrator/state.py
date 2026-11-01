"""LangGraph State — 带循环控制"""

from typing import Annotated, Any, TypedDict
from langgraph.graph.message import add_messages


class PlannerState(TypedDict, total=False):
    user_id: str
    destination: str
    origin: str
    start_date: str
    end_date: str
    days: int
    total_budget: float
    reserve_budget: float
    planning_budget: float
    budget_no_limit: bool
    preferences: list[str]
    preferences_provided: bool
    cuisine_preferences: list[str]
    pace: str
    hotel_star: int
    hotel_budget: float
    meal_budget: float
    travelers: int
    preferred_transport: str
    preferred_transport_provided: bool
    messages: Annotated[list, add_messages]

    daily_plan: list[dict]
    meal_plan: list[dict]
    hotel_plan: dict
    meituan_raw: str
    meituan_hotels: list[dict]
    attraction_details: list[dict]
    food_details: list[dict]
    traffic: dict
    big_traffic: dict
    final_plan: dict

    # 循环控制
    current_stage: str
    retry_count: int
    adjusted_params: dict
    should_retry: bool
    errors: list[str]

    # 天气
    weather_forecast: list[dict]
    weather_impact: list[dict]
    weather_status: str  # "success" | "fallback"
