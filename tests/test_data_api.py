"""补充测试 data API — 城市过滤器 + 天气"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.api.router import app


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestCities:
    @pytest.mark.asyncio
    async def test_cities_with_keyword(self, client):
        resp = await client.get("/api/v1/data/cities?keyword=大理")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert len(data["data"]) >= 1

    @pytest.mark.asyncio
    async def test_cities_popular_false_empty(self, client):
        resp = await client.get("/api/v1/data/cities?popular=false")
        assert resp.status_code == 200
        assert resp.json()["data"] == []

    @pytest.mark.asyncio
    async def test_cities_default(self, client):
        resp = await client.get("/api/v1/data/cities")
        assert resp.status_code == 200
        assert len(resp.json()["data"]) >= 0


class TestWeather:
    @pytest.mark.asyncio
    async def test_weather_no_date(self, client):
        resp = await client.get("/api/v1/data/weather?city=Beijing")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["city"] == "Beijing"
