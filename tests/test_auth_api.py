"""补充测试 app/api/v1/auth.py — 认证接口"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.api.router import app
from app.dependencies import get_current_user


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestSmsCode:
    @pytest.mark.asyncio
    async def test_valid_phone_returns_success(self, client):
        response = await client.post("/api/v1/auth/sms-codes", json={
            "phone": "13800138000",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0

    @pytest.mark.asyncio
    async def test_invalid_phone_format_returns_400(self, client):
        response = await client.post("/api/v1/auth/sms-codes", json={
            "phone": "123",
        })
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_missing_phone_returns_400(self, client):
        response = await client.post("/api/v1/auth/sms-codes", json={})
        assert response.status_code == 400


class TestUserProfile:
    @pytest.mark.asyncio
    async def test_profile_requires_auth(self, client):
        response = await client.get("/api/v1/user/profile")
        assert response.status_code == 401
        assert response.json()["code"] == 20001
