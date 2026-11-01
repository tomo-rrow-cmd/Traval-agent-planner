"""
Weather Impact Calculator — deterministic rules: forecast → quantified impact factors.

Pure functions, no LLM, no network. Converts Amap weather API cast data into
structured WeatherImpact dicts consumed by downstream agents.
"""

from datetime import date as dt, timedelta
from typing import Any


# ---- public API ----

def calculate_weather_impact(
    forecasts: list[dict],
    preferred_transport: str = "transit",
) -> list[dict]:
    """
    Convert raw Amap forecast casts into per-day WeatherImpact dicts.

    Args:
        forecasts: list of Amap cast dicts, each like:
            {"date": "2026-07-14", "dayweather": "晴", "nightweather": "多云",
             "daytemp": "32", "nighttemp": "24", "daywind": "南", "daypower": "3"}
        preferred_transport: user's transport preference ("transit"/"driving"/"walking")

    Returns:
        list of WeatherImpact dicts, one per forecast day, sorted by date
    """
    impacts = []
    for i, fc in enumerate(forecasts):
        impacts.append(_compute_impact(fc, i + 1, preferred_transport))
    return impacts


def build_neutral_impacts(
    days: int,
    start_date: str = "",
    preferred_transport: str = "transit",
) -> list[dict]:
    """
    Returns neutral impact dicts when the weather API fails or returns empty.

    All suitability = 1.0, walking = true, no advice. Does not block pipeline.
    """
    start = dt.fromisoformat(start_date) if start_date else dt.today() + timedelta(days=1)
    impacts = []
    for d in range(days):
        date_str = str(start + timedelta(days=d))
        impacts.append({
            "date": date_str,
            "day_of_trip": d + 1,
            "dayweather": "未知",
            "nightweather": "未知",
            "daytemp": 22,
            "nighttemp": 15,
            "daypower": 2,
            "severity_grade": 0,
            "outdoor_suitability": 1.0,
            "traffic_speed_factor": 1.0,
            "walking_viable": True,
            "preferred_mode": preferred_transport,
            "heat_risk": "none",
            "advice": [],
        })
    return impacts


# ---- internal helpers ----

# Amap has ~50 weather strings. Use keyword matching, not exact match.
SEVERE_KEYWORDS: list[str] = [
    "暴", "飓风", "沙尘暴", "特大暴雨", "冻雨", "冰雹",
    "大暴雨", "烈风", "狂爆风", "热带风暴",
]
POOR_KEYWORDS: list[str] = [
    "大雨", "中雨", "雷阵雨", "大雪", "扬沙", "浓雾",
    "中度霾", "强风", "暴雨", "暴雪", "沙尘", "台风",
    "劲风", "疾风",
]
CAUTION_KEYWORDS: list[str] = [
    "小雨", "阵雨", "雾", "霾", "浮尘", "小雪", "雨夹雪",
    "阵雪", "薄雾", "小到中雨", "中到大雨", "雷雨",
]


def _classify_severity(dayweather: str) -> int:
    """
    0 = excellent (晴 etc), 1 = good (阴/多云), 2 = caution,
    3 = poor, 4 = severe
    """
    w = str(dayweather or "").strip()
    if not w:
        return 0
    # Check severe first (most dangerous)
    for kw in SEVERE_KEYWORDS:
        if kw in w:
            return 4
    for kw in POOR_KEYWORDS:
        if kw in w:
            return 3
    for kw in CAUTION_KEYWORDS:
        if kw in w:
            return 2
    # Multi-cloud / overcast is a mild concern
    if "多云" in w or "阴" in w:
        return 1
    return 0  # 晴, 少云, etc.


def _weather_factor(severity: int) -> float:
    return {0: 1.0, 1: 0.85, 2: 0.55, 3: 0.25, 4: 0.05}.get(severity, 0.85)


def _temp_factor(daytemp: float) -> float:
    t = float(daytemp)
    if 15 <= t <= 28:
        return 1.0
    if 28 < t <= 32:
        return 0.85
    if 32 < t <= 35:
        return 0.65
    if 35 < t <= 38:
        return 0.4
    if t > 38:
        return 0.2
    if 5 <= t < 15:
        return 0.8
    if 0 <= t < 5:
        return 0.6
    return 0.3  # < 0°C


def _wind_factor(daypower: float) -> float:
    p = float(daypower)
    if p <= 3:
        return 1.0
    if p <= 5:
        return 0.9
    if p <= 7:
        return 0.5
    return 0.15  # ≥ 8


def _compute_outdoor_suitability(severity: int, daytemp: float, daypower: float) -> float:
    return round(_weather_factor(severity) * _temp_factor(daytemp) * _wind_factor(daypower), 4)


def _traffic_speed_factor(severity: int) -> float:
    return {0: 1.0, 1: 0.95, 2: 0.85, 3: 0.7, 4: 0.5}.get(severity, 0.95)


def _is_walking_viable(severity: int, daytemp: float, daypower: float) -> bool:
    return severity < 3 and float(daytemp) <= 36 and float(daytemp) >= -5 and float(daypower) < 7


def _compute_preferred_mode(severity: int, daytemp: float, preferred: str) -> str:
    if severity >= 3:
        return "transit"
    if float(daytemp) > 35:
        return "transit"
    return preferred


def _classify_heat_risk(daytemp: float) -> str:
    t = float(daytemp)
    if t >= 38:
        return "extreme"
    if t >= 35:
        return "high"
    if t >= 32:
        return "medium"
    if t >= 28:
        return "low"
    return "none"


def _generate_advice(impact: dict) -> list[str]:
    tips: list[str] = []
    outdoor_suit = impact.get("outdoor_suitability", 1.0)
    severity = impact.get("severity_grade", 0)
    dayweather = impact.get("dayweather", "")
    heat_risk = impact.get("heat_risk", "none")
    walking_viable = impact.get("walking_viable", True)

    if outdoor_suit < 0.3:
        tips.append("建议将户外活动调整为室内场所（博物馆、美术馆、购物中心）")
    elif outdoor_suit < 0.6:
        tips.append("户外活动请注意天气变化，优先安排在上午")
    if severity >= 3:
        tips.append("携带雨具，出行预留额外时间")
    if severity >= 2:
        tips.append("路面湿滑，注意步行安全")
    if heat_risk in ("high", "extreme"):
        tips.append("午后避免户外活动，注意防暑降温")
    if not walking_viable:
        tips.append("不建议步行，优先选择地铁或打车")
    if outdoor_suit >= 0.8 and severity <= 1:
        tips.append("天气晴好，适合户外活动")

    return tips


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Parse a possibly-range Amap value like '1-3', '<3', '3' to float (taking max)."""
    if value is None:
        return default
    s = str(value).strip()
    if not s:
        return default
    # Remove directional prefixes
    s = s.lstrip("<>≤≥~")
    # Handle range: "1-3" → take the max (right side)
    if "-" in s:
        parts = s.split("-")
        try:
            return max(float(p) for p in parts)
        except ValueError:
            return default
    try:
        return float(s)
    except ValueError:
        return default


def _compute_impact(fc: dict, day_of_trip: int, preferred_transport: str) -> dict:
    dayweather = str(fc.get("dayweather", "") or "")
    nightweather = str(fc.get("nightweather", "") or "")
    daytemp = _safe_float(fc.get("daytemp"), default=22)
    nighttemp = _safe_float(fc.get("nighttemp"), default=15)
    daypower = _safe_float(fc.get("daypower"), default=2)

    severity = _classify_severity(dayweather)

    # Consider night weather too: if night is worse, upgrade severity
    night_severity = _classify_severity(nightweather)
    severity = max(severity, night_severity)

    outdoor_suitability = _compute_outdoor_suitability(severity, daytemp, daypower)
    traffic_speed = _traffic_speed_factor(severity)
    walking = _is_walking_viable(severity, daytemp, daypower)
    pref_mode = _compute_preferred_mode(severity, daytemp, preferred_transport)
    heat = _classify_heat_risk(daytemp)

    impact = {
        "date": fc.get("date", ""),
        "day_of_trip": day_of_trip,
        "dayweather": dayweather,
        "nightweather": nightweather,
        "daytemp": daytemp,
        "nighttemp": nighttemp,
        "daypower": daypower,
        "severity_grade": severity,
        "outdoor_suitability": outdoor_suitability,
        "traffic_speed_factor": traffic_speed,
        "walking_viable": walking,
        "preferred_mode": pref_mode,
        "heat_risk": heat,
        "advice": [],
    }
    impact["advice"] = _generate_advice(impact)
    return impact
