"""测试 WeatherAgent 的高德天气 key 判断。"""

import pytest
from unittest.mock import MagicMock

from app.agents.weather_agent import WeatherAgent


@pytest.mark.asyncio
async def test_fetch_forecasts_uses_amap_key(monkeypatch):
    agent = WeatherAgent(MagicMock())
    forecasts = [{"date": "2026-08-01", "dayweather": "晴"}]
    captured = {}

    async def fake_get_forecast_for_dates(city, start_date, end_date):
        captured["city"] = city
        captured["start_date"] = start_date
        captured["end_date"] = end_date
        return forecasts

    monkeypatch.setattr("app.agents.weather_agent.qweather_service.api_key", "amap-key")
    monkeypatch.setattr(
        "app.agents.weather_agent.qweather_service.get_forecast_for_dates",
        fake_get_forecast_for_dates,
    )

    result = await agent._fetch_forecasts("北京", "2026-08-01", "2026-08-02")

    assert result == forecasts
    assert captured["city"] == "北京"


@pytest.mark.asyncio
async def test_fetch_forecasts_without_amap_key_returns_empty(monkeypatch):
    agent = WeatherAgent(MagicMock())

    async def should_not_call(*args, **kwargs):
        raise AssertionError("weather API should not be called without an API key")

    monkeypatch.setattr("app.agents.weather_agent.qweather_service.api_key", "")
    monkeypatch.setattr(
        "app.agents.weather_agent.qweather_service.get_forecast_for_dates",
        should_not_call,
    )

    result = await agent._fetch_forecasts("北京", "2026-08-01", "2026-08-02")

    assert result == []


@pytest.mark.asyncio
async def test_generate_impact_factors_merges_partial_forecast_by_date(monkeypatch):
    agent = WeatherAgent(MagicMock())
    forecasts = [
        {
            "date": "2099-08-01",
            "dayweather": "晴",
            "nightweather": "多云",
            "daytemp": "30",
            "nighttemp": "20",
            "daypower": "2",
        },
        {"date": "invalid-date", "dayweather": "大雨"},
        {
            "date": "2099-08-03",
            "dayweather": "暴雨",
            "nightweather": "大雨",
            "daytemp": "24",
            "nighttemp": "18",
            "daypower": "5",
        },
    ]

    async def fake_fetch(*args, **kwargs):
        _ = args, kwargs
        return forecasts

    monkeypatch.setattr(agent, "_fetch_forecasts", fake_fetch)

    result = await agent.generate_impact_factors(
        destination="北京",
        start_date="2099-08-01",
        end_date="2099-08-04",
        days=4,
        preferred_transport="步行",
    )

    assert [item["date"] for item in result["forecasts"]] == [
        "2099-08-01",
        "2099-08-03",
    ]
    assert [item["date"] for item in result["impacts"]] == [
        "2099-08-01",
        "2099-08-02",
        "2099-08-03",
        "2099-08-04",
    ]
    assert result["impacts"][0]["dayweather"] == "晴"
    assert result["impacts"][1]["dayweather"] == "未知"
    assert result["impacts"][2]["dayweather"] == "暴雨"
    assert result["impacts"][2]["day_of_trip"] == 3
    assert result["impacts"][3]["dayweather"] == "未知"


@pytest.mark.asyncio
async def test_generate_impact_factors_uses_full_fallback_without_forecast(monkeypatch):
    agent = WeatherAgent(MagicMock())

    async def fake_fetch(*args, **kwargs):
        _ = args, kwargs
        return []

    monkeypatch.setattr(agent, "_fetch_forecasts", fake_fetch)

    result = await agent.generate_impact_factors(
        destination="北京",
        start_date="2099-12-01",
        end_date="2099-12-03",
        days=3,
        preferred_transport="地铁",
    )

    assert result["forecasts"] == []
    assert [item["date"] for item in result["impacts"]] == [
        "2099-12-01",
        "2099-12-02",
        "2099-12-03",
    ]
    assert all(item["traffic_speed_factor"] == 1.0 for item in result["impacts"])
