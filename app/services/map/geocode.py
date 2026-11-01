"""
地理编码与距离计算
"""

import math


def haversine_distance(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """
    使用 Haversine 公式计算两点间的球面距离。

    Returns:
        float: 距离（千米）
    """
    R = 6371.0  # 地球平均半径（km）

    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def estimate_travel_time(
    distance_km: float,
    mode: str = "walking",
) -> float:
    """
    估算交通时长。

    Args:
        distance_km: 距离（千米）
        mode: 交通方式（walking / driving / transit）

    Returns:
        float: 预计时长（分钟）
    """
    speeds = {
        "walking": 5.0,    # 步行 5 km/h
        "driving": 30.0,   # 驾车 30 km/h（城市路况）
        "transit": 20.0,   # 公共交通 20 km/h
        "subway": 35.0,    # 地铁 35 km/h
    }
    speed = speeds.get(mode, 20.0)
    return (distance_km / speed) * 60
