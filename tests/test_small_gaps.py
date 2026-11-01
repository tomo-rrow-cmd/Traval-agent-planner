"""精准打击剩余小缺口 — 仅保留有效测试"""

import pytest


class TestSecurityEdges:
    def test_token_roundtrip(self):
        from app.core.security import create_access_token, decode_access_token
        token = create_access_token("user-1", {"role": "admin"})
        payload = decode_access_token(token)
        assert payload["sub"] == "user-1"
        assert payload["role"] == "admin"

    def test_refresh_token_roundtrip(self):
        from app.core.security import create_refresh_token, decode_refresh_token
        token = create_refresh_token("user-x")
        payload = decode_refresh_token(token)
        assert payload["sub"] == "user-x"

    def test_expired_token_format(self):
        from app.core.security import create_access_token
        token = create_access_token("u1")
        assert token.count(".") == 2


class TestExceptions:
    def test_all_exceptions(self):
        from app.exceptions import (
            UnauthorizedException, NotFoundException,
            BadRequestException, ExternalServiceException,
            LLMServiceException, NotImplementedAppException,
        )
        for exc_cls, msg in [
            (UnauthorizedException, "unauth"),
            (NotFoundException, "missing"),
            (BadRequestException, "bad"),
            (ExternalServiceException, "ext"),
        ]:
            e = exc_cls(msg)
            assert str(e) == msg

        # 覆盖 LLMServiceException 和 NotImplementedAppException 的 __init__
        e1 = LLMServiceException()
        assert e1.code == 60003
        e2 = NotImplementedAppException()
        assert e2.code == 70002


class TestParsePriceRange:
    def test_all_branches(self):
        from app.api.v1.data import _parse_price_range
        assert _parse_price_range("200-500") == 500.0
        assert _parse_price_range(None) is None
        assert _parse_price_range("") is None
        assert _parse_price_range("invalid") is None


class TestGeocode:
    def test_haversine_distance(self):
        from app.services.map.geocode import haversine_distance
        assert haversine_distance(39.9, 116.4, 39.9, 116.4) < 0.01
        d = haversine_distance(39.9, 116.4, 31.2, 121.4)
        assert d > 500


class TestLogger:
    def test_logger_can_be_imported(self):
        from app.utils.logger import logger
        assert logger is not None


class TestBudgetTools:
    def test_imports_budget_tools(self):
        from app.agents.tools.budget_tools import BUDGET_TOOLS
        assert len(BUDGET_TOOLS) == 2
        assert BUDGET_TOOLS[0]["function"]["name"] == "calculate_budget"


class TestSecurityTokenType:
    def test_access_token_rejected_as_refresh(self):
        """decode_refresh_token 拒绝 access token"""
        from app.core.security import create_access_token, decode_refresh_token
        import jwt as pyjwt
        token = create_access_token("u1")
        with pytest.raises(Exception):
            decode_refresh_token(token)

    def test_refresh_token_rejected_as_access(self):
        """decode_access_token 拒绝 refresh token"""
        from app.core.security import create_refresh_token, decode_access_token
        import jwt as pyjwt
        token = create_refresh_token("u1")
        with pytest.raises(Exception):
            decode_access_token(token)


class TestRouterLifespan:
    @pytest.mark.asyncio
    async def test_meituan_init_in_lifespan(self, monkeypatch):
        """启动时 meituan.sync_config_from_env 被调用"""
        called = False
        closed = False

        def fake_sync():
            nonlocal called
            called = True

        import app.api.router as router_module
        monkeypatch.setattr(router_module.meituan, "sync_config_from_env", fake_sync)

        def fake_validate():
            return type("Health", (), {"status": "empty", "collections": {}})()

        def fake_close():
            nonlocal closed
            closed = True

        monkeypatch.setattr(router_module.vector_store, "validate", fake_validate)
        monkeypatch.setattr(router_module.vector_store, "close", fake_close)

        # 触发 lifespan
        async with router_module.lifespan(router_module.app):
            pass

        assert called
        assert closed

    @pytest.mark.asyncio
    async def test_chroma_failure_stops_startup_and_releases_client(self, monkeypatch):
        import app.api.router as router_module

        closed = False

        def fail_validate():
            raise RuntimeError("broken chroma")

        def fake_close():
            nonlocal closed
            closed = True

        monkeypatch.setattr(router_module.vector_store, "validate", fail_validate)
        monkeypatch.setattr(router_module.vector_store, "close", fake_close)

        with pytest.raises(RuntimeError, match="broken chroma"):
            async with router_module.lifespan(router_module.app):
                pass

        assert closed is True


class TestImpactEdges:
    def test_high_heat_produces_warning(self):
        """高温(>=37°C) → heat_risk=high"""
        from app.services.weather.impact import _compute_impact
        fc = {
            "dayweather": "晴", "daytemp": "39", "nighttemp": "30",
            "daypower": "2", "day_of_trip": 1, "date": "2026-08-01",
        }
        result = _compute_impact(fc, day_of_trip=1, preferred_transport="地铁")
        assert isinstance(result, dict)
        assert result.get("heat_risk") in ("high", "extreme")

    def test_invalid_temp_triggers_parse_fallback(self):
        """含 '-' 但非数字的温度 → _parse_float 的 range 分支返回 default"""
        from app.services.weather.impact import _compute_impact
        fc = {
            "dayweather": "多云", "daytemp": "invalid-range", "nighttemp": "N/A",
            "daypower": "2", "day_of_trip": 1, "date": "2026-08-01",
        }
        result = _compute_impact(fc, day_of_trip=1, preferred_transport="步行")
        assert isinstance(result, dict)

    def test_non_numeric_temp_simple_branch(self):
        """不含 '-' 的非数字温度 → _parse_float 简单分支返回 default"""
        from app.services.weather.impact import _compute_impact
        fc = {
            "dayweather": "多云", "daytemp": "??", "nighttemp": "--",
            "daypower": "2", "day_of_trip": 1, "date": "2026-08-01",
        }
        result = _compute_impact(fc, day_of_trip=1, preferred_transport="步行")
        assert isinstance(result, dict)
