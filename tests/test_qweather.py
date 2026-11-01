"""测试 app/services/weather/qweather.py — 天气服务（mock httpx）"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.weather.qweather import QWeatherService


@pytest.fixture
def service():
    return QWeatherService()


class TestQWeather:
    @pytest.mark.asyncio
    async def test_search_city_returns_common_adcode(self, service):
        result = await service.search_city("北京")
        assert result == "110000"

    @pytest.mark.asyncio
    async def test_search_city_falls_back_to_district_api(self, service, monkeypatch):
        captured = {}

        async def fake_get_district(self, params):
            captured.update(params)
            return {"districts": [{"name": "大理白族自治州", "adcode": "532900"}]}

        monkeypatch.setattr(QWeatherService, "_get_district", fake_get_district)
        result = await service.search_city("大理")

        assert result == "532900"
        assert captured["keywords"] == "大理"
        assert captured["subdistrict"] == 0

    @pytest.mark.asyncio
    async def test_get_current_weather(self, service, monkeypatch):
        captured = {}

        async def fake_get(self, params):
            captured.update(params)
            return {"lives": [{
                "temperature": "25", "weather": "晴",
                "winddirection": "南", "windpower": "3",
                "humidity": "60", "reporttime": "2026-07-14 10:00:00",
            }]}

        monkeypatch.setattr(QWeatherService, "_get", fake_get)
        result = await service.get_current_weather("北京")
        assert result["temp"] == "25"
        assert result["text"] == "晴"
        assert captured["city"] == "110000"
        assert captured["extensions"] == "base"

    @pytest.mark.asyncio
    async def test_get_current_weather_empty(self, service, monkeypatch):
        async def fake_get(self, params):
            return {"lives": []}
        async def fake_search_city(self, city_name):
            return "110000"
        monkeypatch.setattr(QWeatherService, "search_city", fake_search_city)
        monkeypatch.setattr(QWeatherService, "_get", fake_get)
        result = await service.get_current_weather("火星")
        assert result == {}

    @pytest.mark.asyncio
    async def test_get_7day_forecast(self, service, monkeypatch):
        captured = {}

        async def fake_get(self, params):
            captured.update(params)
            return {"forecasts": [{"casts": [
                {"date": "2026-07-14", "dayweather": "晴"},
                {"date": "2026-07-15", "dayweather": "多云"},
            ]}]}
        monkeypatch.setattr(QWeatherService, "_get", fake_get)
        result = await service.get_7day_forecast("北京")
        assert len(result) == 2
        assert captured["city"] == "110000"
        assert captured["extensions"] == "all"

    @pytest.mark.asyncio
    async def test_get_7day_forecast_empty(self, service, monkeypatch):
        async def fake_get(self, params):
            return {"forecasts": []}
        monkeypatch.setattr(QWeatherService, "_get", fake_get)
        result = await service.get_7day_forecast("北京")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_forecast_for_dates(self, service, monkeypatch):
        from datetime import date
        async def fake_get(self, params):
            return {"forecasts": [{"casts": [
                {"date": "2026-08-01", "dayweather": "晴"},
                {"date": "2026-08-02", "dayweather": "雨"},
                {"date": "2026-08-03", "dayweather": "多云"},
            ]}]}
        monkeypatch.setattr(QWeatherService, "_get", fake_get)
        result = await service.get_forecast_for_dates("北京", date(2026, 8, 1), date(2026, 8, 2))
        assert len(result) == 2  # 只有 8/1 和 8/2

    @pytest.mark.asyncio
    async def test_life_index(self, service):
        result = await service.get_life_index("北京")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_http_error(self, service, monkeypatch):
        """异常路径: HTTP 非 200 → ExternalServiceException"""
        import httpx
        from app.exceptions import ExternalServiceException

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_resp)

        monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: mock_client)

        with pytest.raises(ExternalServiceException, match="HTTP 500"):
            await service._get({"city": "test"})

    @pytest.mark.asyncio
    async def test_get_api_error_status(self, service, monkeypatch):
        """异常路径: API status != 1 → ExternalServiceException"""
        import httpx
        from app.exceptions import ExternalServiceException

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json = MagicMock(return_value={"status": "0", "info": "Invalid key"})
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=mock_resp)

        monkeypatch.setattr(httpx, "AsyncClient", lambda timeout: mock_client)

        with pytest.raises(ExternalServiceException, match="Invalid key"):
            await service._get({"city": "test"})
