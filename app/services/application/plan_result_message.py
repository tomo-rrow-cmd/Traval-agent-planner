"""Compact chat message for a completed travel plan."""

from typing import Any


PLAN_RESULT_FORMAT = "compact_v1"


def build_plan_result_message(summary: dict[str, Any] | None) -> str:
    data = summary if isinstance(summary, dict) else {}
    destination = _text(data.get("destination"))
    origin = _text(data.get("origin"))
    days = _positive_int(data.get("days"))
    trip_config = data.get("trip_config")
    trip_config = trip_config if isinstance(trip_config, dict) else {}
    travelers = _positive_int(
        trip_config.get("travelers")
        or data.get("travelers")
        or data.get("people_count")
    )

    if destination and days:
        title = f"{destination}{days}日方案"
    elif destination:
        title = f"{destination}旅行方案"
    else:
        title = "旅行方案"

    lines = [f"✅ {title}已生成"]
    route_parts = []
    if origin and destination:
        route_parts.append(f"{origin} → {destination}")
    elif destination:
        route_parts.append(destination)
    elif origin:
        route_parts.append(origin)
    if days:
        route_parts.append(f"{days}天")
    if travelers:
        route_parts.append(f"{travelers}人")
    if route_parts:
        lines.append(" · ".join(route_parts))

    budget = data.get("budget")
    budget = budget if isinstance(budget, dict) else {}
    estimated = _positive_number(
        budget.get("actual_total"),
        data.get("estimated_cost"),
    )
    total = _positive_number(
        budget.get("total_budget"),
        data.get("total_budget"),
    )
    budget_parts = []
    if estimated is not None:
        budget_parts.append(f"预计 ¥{_format_number(estimated)}")
    if total is not None:
        budget_parts.append(f"预算 ¥{_format_number(total)}")
    if budget_parts:
        lines.append(" / ".join(budget_parts))

    return "\n".join(lines[:3])


def _text(value: Any) -> str:
    return str(value or "").strip()


def _positive_int(value: Any) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def _positive_number(*values: Any) -> float | None:
    for value in values:
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if number > 0:
            return number
    return None


def _format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")
