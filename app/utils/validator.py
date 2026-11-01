"""
数据校验工具
"""

from datetime import date, timedelta
from typing import Any


def resolve_trip_dates(
    start_date: Any = None,
    end_date: Any = None,
    days: Any = None,
    today: date | str | None = None,
) -> dict[str, Any]:
    """统一解析并校验旅行日期范围。"""
    today_date = _coerce_today(today)
    start_raw = _date_text(start_date)
    end_raw = _date_text(end_date)
    day_count = _to_positive_int(days)

    if not start_raw:
        return _date_error("missing_start_date", "请先提供明确的出发日期")
    if not end_raw and day_count <= 0:
        return _date_error("missing_duration", "请提供行程天数或返程日期")

    start = _parse_iso_date(start_raw)
    end = _parse_iso_date(end_raw) if end_raw else None
    if start is None or (end_raw and end is None):
        return _date_error("invalid_format", "日期格式无效，请使用 YYYY-MM-DD 格式")

    if start < today_date:
        return _date_error("past_start_date", "出发日期不能早于今天")

    if end is None:
        end = start + timedelta(days=day_count - 1)
    else:
        if end < start:
            return _date_error("end_before_start", "返程日期不能早于出发日期")
        derived_days = (end - start).days + 1
        if day_count > 0 and day_count != derived_days:
            return _date_error(
                "date_days_conflict",
                "日期范围与行程天数不一致",
                provided_days=day_count,
                derived_days=derived_days,
            )
        day_count = derived_days

    if day_count > 30:
        return _date_error("exceeds_max_days", "行程天数不能超过 30 天")

    return {
        "ok": True,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "days": day_count,
    }


def validate_date_range(
    start_date: str,
    end_date: str,
    today: date | str | None = None,
) -> tuple[bool, str]:
    """
    校验日期范围是否合法。

    Returns:
        (is_valid, error_message)
    """
    result = resolve_trip_dates(start_date=start_date, end_date=end_date, today=today)
    return bool(result.get("ok")), str(result.get("message", ""))


def _date_error(error_code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "error_code": error_code, "message": message, **extra}


def _coerce_today(value: date | str | None) -> date:
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        parsed = _parse_iso_date(value.strip())
        if parsed is not None:
            return parsed
    return date.today()


def _date_text(value: Any) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip() if value is not None else ""


def _parse_iso_date(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _to_positive_int(value: Any) -> int:
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return 0
    return number if number > 0 else 0


def validate_budget(budget: float, days: int, travelers: int) -> tuple[bool, str]:
    """
    校验预算是否合理。

    Returns:
        (is_valid, error_message)
    """
    if budget <= 0:
        return False, "预算必须大于 0"

    per_person_per_day = budget / travelers / days if travelers > 0 and days > 0 else budget

    if per_person_per_day < 100:
        return False, f"人均每日预算过低（¥{per_person_per_day:.0f}），建议至少 ¥100/天"

    return True, ""


def sanitize_input(text: str, max_length: int = 500) -> str:
    """清理用户输入"""
    if not text:
        return ""
    # 去除首尾空白，截断过长输入
    return text.strip()[:max_length]


def validate_required_fields(data: dict[str, Any], required: list[str]) -> list[str]:
    """检查必填字段，返回缺失字段列表"""
    return [field for field in required if not data.get(field)]
