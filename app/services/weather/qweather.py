"""天气适配器 — 高德天气 API（保留历史 QWeatherService 类名）"""

from datetime import date
from typing import Optional

import httpx

from app.config import settings
from app.exceptions import ExternalServiceException


class QWeatherService:
    """天气服务（高德 API）"""

    BASE_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
    DISTRICT_URL = "https://restapi.amap.com/v3/config/district"
    COMMON_CITY_ADCODES = {
        "北京": "110000",
        "北京市": "110000",
        "上海": "310000",
        "上海市": "310000",
        "天津": "120000",
        "天津市": "120000",
        "重庆": "500000",
        "重庆市": "500000",
        "广州": "440100",
        "广州市": "440100",
        "深圳": "440300",
        "深圳市": "440300",
        "成都": "510100",
        "成都市": "510100",
        "杭州": "330100",
        "杭州市": "330100",
        "南京": "320100",
        "南京市": "320100",
        "武汉": "420100",
        "武汉市": "420100",
        "西安": "610100",
        "西安市": "610100",
        "苏州": "320500",
        "苏州市": "320500",
        "厦门": "350200",
        "厦门市": "350200",
        "青岛": "370200",
        "青岛市": "370200",
        "长沙": "430100",
        "长沙市": "430100",
        "郑州": "410100",
        "郑州市": "410100",
    }

    def __init__(self):
        self.api_key = settings.AMAP_API_KEY
        self._city_cache: dict[str, str] = {}

    async def _request(self, url: str, params: dict) -> dict:
        params["key"] = self.api_key
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                raise ExternalServiceException(f"天气 API HTTP {resp.status_code}")
            data = resp.json()
            if data.get("status") != "1":
                raise ExternalServiceException(f"天气 API: {data.get('info')}")
            return data

    async def _get(self, params: dict) -> dict:
        return await self._request(self.BASE_URL, params)

    async def _get_district(self, params: dict) -> dict:
        return await self._request(self.DISTRICT_URL, params)

    async def search_city(self, city_name: str) -> Optional[str]:
        """城市名 → adcode。高德天气 city 参数按文档应传城市编码。"""
        name = str(city_name or "").strip()
        if not name:
            return None
        if name.isdigit() and len(name) == 6:
            return name
        if name in self._city_cache:
            return self._city_cache[name]

        candidates = [name]
        if name.endswith("市"):
            candidates.append(name[:-1])
        for candidate in candidates:
            adcode = self.COMMON_CITY_ADCODES.get(candidate)
            if adcode:
                self._city_cache[name] = adcode
                return adcode

        data = await self._get_district({
            "keywords": name,
            "subdistrict": 0,
            "extensions": "base",
        })
        for district in data.get("districts", []):
            adcode = district.get("adcode")
            if isinstance(adcode, str) and adcode:
                self._city_cache[name] = adcode
                return adcode
        return None

    async def get_current_weather(self, city: str) -> dict:
        """实时天气"""
        city_code = await self.search_city(city)
        if not city_code:
            return {}
        data = await self._get({"city": city_code, "extensions": "base"})
        lives = data.get("lives", [])
        if lives:
            live = lives[0]
            return {
                "temp": live.get("temperature"),
                "feelsLike": live.get("temperature"),
                "text": live.get("weather"),
                "windDir": live.get("winddirection"),
                "windScale": live.get("windpower"),
                "humidity": live.get("humidity"),
                "reportTime": live.get("reporttime"),
            }
        return {}

    async def get_7day_forecast(self, city: str) -> list[dict]:
        """获取多日预报"""
        city_code = await self.search_city(city)
        if not city_code:
            return []
        data = await self._get({"city": city_code, "extensions": "all"})
        forecasts = data.get("forecasts", [])
        if forecasts:
            return forecasts[0].get("casts", [])
        return []

    async def get_forecast_for_dates(
        self, city: str, start_date: date, end_date: date,
    ) -> list[dict]:
        """指定日期范围的预报"""
        all_fc = await self.get_7day_forecast(city)
        filtered = []
        for forecast in all_fc:
            try:
                forecast_date = date.fromisoformat(forecast.get("date", ""))
            except ValueError:
                continue
            if start_date <= forecast_date <= end_date:
                filtered.append(forecast)
        return filtered

    async def get_life_index(self, city: str, index_type: str = "0") -> list[dict]:
        """生活指数（高德暂不支持，返回空）"""
        return []


qweather_service = QWeatherService()
