"""
高德地图封装 - 封装高德地图 Web API
"""

from typing import Optional

import httpx

from app.config import settings
from app.exceptions import ExternalServiceException


class AmapService:
    """高德地图服务"""

    BASE_URL = "https://restapi.amap.com/v3"

    def __init__(self):
        self.api_key = settings.AMAP_API_KEY

    async def _request(self, endpoint: str, params: dict) -> dict:
        """通用请求方法"""
        params["key"] = self.api_key
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.BASE_URL}/{endpoint}", params=params)
            if response.status_code != 200:
                raise ExternalServiceException(f"高德地图 API 错误: {response.text}")
            data = response.json()
            if data.get("status") != "1":
                raise ExternalServiceException(f"高德地图 API 错误: {data.get('info')}")
            return data

    async def search_poi(
        self,
        keywords: str,
        city: str,
        types: Optional[str] = None,
        offset: int = 20,
        page: int = 1,
    ) -> list[dict]:
        """
        POI 搜索（景点、餐厅、酒店等）。
        """
        params = {
            "keywords": keywords,
            "city": city,
            "offset": offset,
            "page": page,
        }
        if types:
            params["types"] = types

        data = await self._request("place/text", params)
        return data.get("pois", [])

    async def geocode(self, address: str, city: Optional[str] = None) -> Optional[dict]:
        """
        地理编码：地址 → 经纬度。
        """
        params = {"address": address}
        if city:
            params["city"] = city

        data = await self._request("geocode/geo", params)
        geocodes = data.get("geocodes", [])
        if geocodes:
            location = geocodes[0]["location"].split(",")
            return {
                "longitude": float(location[0]),
                "latitude": float(location[1]),
                "formatted_address": geocodes[0].get("formatted_address"),
            }
        return None

    async def reverse_geocode(self, longitude: float, latitude: float) -> Optional[dict]:
        """
        逆地理编码：经纬度 → 地址。
        """
        params = {"location": f"{longitude},{latitude}"}
        data = await self._request("geocode/regeo", params)
        regeocode = data.get("regeocode", {})
        return regeocode

    async def route_planning(
        self,
        origin: str,       # 起点坐标 "lng,lat"
        destination: str,  # 终点坐标 "lng,lat"
        route_type: str = "transit",  # driving / walking / transit
        city: Optional[str] = None,
    ) -> dict:
        """
        路径规划。
        """
        type_map = {
            "driving": "direction/driving",
            "walking": "direction/walking",
            "transit": "direction/transit/integrated",
        }
        endpoint = type_map.get(route_type, "direction/transit/integrated")

        params = {"origin": origin, "destination": destination}
        if route_type == "transit" and city:
            params["city"] = city
        data = await self._request(endpoint, params)
        return data.get("route", {})


amap_service = AmapService()
