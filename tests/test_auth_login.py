"""测试 auth API 登录/注册/刷新 — mock DB 完整版"""

import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport
from app.api.router import app
from app.core.security import hash_password
from app.dependencies import get_current_user


def make_fake_db(existing_user=None):
    """创建 mock DB session"""
    class FakeResult:
        def __init__(self, user):
            self._user = user
        def scalar_one_or_none(self):
            return self._user

    class FakeDB:
        def __init__(self):
            self.added = []
        async def execute(self, stmt):
            return FakeResult(existing_user)
        async def commit(self):
            pass
        async def rollback(self):
            pass
        async def close(self):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *a):
            pass
        def add(self, obj):
            if not getattr(obj, "id", None):
                obj.id = str(uuid.uuid4())

    return FakeDB()


@pytest.fixture
def client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_new_user(self, client, monkeypatch):
        db = make_fake_db()
        monkeypatch.setattr("app.api.v1.auth.async_session_factory", lambda: db)
        monkeypatch.setattr("app.db.session.async_session_factory", lambda: db)

        resp = await client.post("/api/v1/auth/register", json={
            "phone": "13800138001", "password": "secure123", "nickname": "测试",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == 0
        assert data["data"]["access_token"]
        assert data["data"]["user"]["nickname"] == "测试"

class TestLogin:
    @pytest.mark.asyncio
    async def test_phone_login_auto_register(self, client, monkeypatch):
        db = make_fake_db()
        monkeypatch.setattr("app.api.v1.auth.async_session_factory", lambda: db)
        monkeypatch.setattr("app.db.session.async_session_factory", lambda: db)

        resp = await client.post("/api/v1/auth/sessions", json={
            "phone": "13800138002", "code": "123456", "method": "phone",
        })
        assert resp.status_code == 200
        assert resp.json()["code"] == 0

    @pytest.mark.asyncio
    async def test_wrong_code(self, client, monkeypatch):
        db = make_fake_db()
        monkeypatch.setattr("app.api.v1.auth.async_session_factory", lambda: db)
        monkeypatch.setattr("app.db.session.async_session_factory", lambda: db)

        resp = await client.post("/api/v1/auth/sessions", json={
            "phone": "13800138002", "code": "000000", "method": "phone",
        })
        assert resp.json()["code"] == 20001

    @pytest.mark.asyncio
    async def test_password_login_success(self, client, monkeypatch):
        from app.db.models.user import User
        user = User()
        user.id = "u-pwd"
        user.phone = "13800138003"
        user.hashed_password = hash_password("correct")
        user.nickname = "pwd"

        class LoginDB:
            def __init__(self):
                self.added = []
            async def execute(self, stmt):
                class R:
                    def scalar_one_or_none(self_):
                        return user
                return R()
            async def commit(self): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): pass

        monkeypatch.setattr("app.api.v1.auth.async_session_factory", lambda: LoginDB())
        monkeypatch.setattr("app.db.session.async_session_factory", lambda: LoginDB())

        resp = await client.post("/api/v1/auth/sessions", json={
            "phone": "13800138003", "password": "correct", "method": "password",
        })
        assert resp.json()["code"] == 0


class TestRefreshToken:
    @pytest.mark.asyncio
    async def test_invalid_token(self, client, monkeypatch):
        db = make_fake_db()
        monkeypatch.setattr("app.api.v1.auth.async_session_factory", lambda: db)
        monkeypatch.setattr("app.db.session.async_session_factory", lambda: db)

        resp = await client.post("/api/v1/auth/tokens", json={
            "refresh_token": "invalid.token",
        })
        assert resp.json()["code"] == 20001

    @pytest.mark.asyncio
    async def test_valid_token_user_deleted(self, client, monkeypatch):
        from app.core.security import create_refresh_token
        token = create_refresh_token("deleted-user")

        db = make_fake_db()  # no existing user
        monkeypatch.setattr("app.api.v1.auth.async_session_factory", lambda: db)
        monkeypatch.setattr("app.db.session.async_session_factory", lambda: db)

        resp = await client.post("/api/v1/auth/tokens", json={
            "refresh_token": token,
        })
        # User query returns None → 用户不存在
        assert resp.json()["code"] == 20001


class TestLogout:
    @pytest.mark.asyncio
    async def test_logout_authenticated(self, monkeypatch):
        async def override_user():
            return {"user_id": "u1", "phone": "13800138000"}

        app.dependency_overrides[get_current_user] = override_user
        client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
        try:
            resp = await client.delete("/api/v1/auth/sessions/current")
            assert resp.status_code == 200
            assert resp.json()["code"] == 0
        finally:
            app.dependency_overrides.clear()
