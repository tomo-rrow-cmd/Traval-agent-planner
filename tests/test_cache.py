"""测试 app/utils/cache.py — Redis 缓存（mock）"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.utils.cache import RedisCache, cache


class TestRedisCache:
    @pytest.mark.asyncio
    async def test_get_without_connection_returns_none(self):
        c = RedisCache()
        assert await c.get("key") is None

    @pytest.mark.asyncio
    async def test_set_without_connection_is_noop(self):
        c = RedisCache()
        await c.set("key", "value")
        # 不应崩溃

    @pytest.mark.asyncio
    async def test_delete_without_connection_is_noop(self):
        c = RedisCache()
        await c.delete("key")

    @pytest.mark.asyncio
    async def test_exists_without_connection_returns_false(self):
        c = RedisCache()
        assert await c.exists("key") is False

    @pytest.mark.asyncio
    async def test_get_returns_json_parsed_value(self):
        c = RedisCache()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value='{"name": "test"}')
        c.redis = mock_redis

        result = await c.get("key")
        assert result == {"name": "test"}

    @pytest.mark.asyncio
    async def test_get_returns_raw_string_on_json_error(self):
        c = RedisCache()
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value="not-json")
        c.redis = mock_redis

        result = await c.get("key")
        assert result == "not-json"

    @pytest.mark.asyncio
    async def test_set_dict_serializes_to_json(self):
        c = RedisCache()
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        c.redis = mock_redis

        await c.set("key", {"name": "value"}, expire=600)
        mock_redis.set.assert_called_once()
        args = mock_redis.set.call_args
        assert "key" in args[0]
        assert "ex" in args[1] or args[1].get("ex") == 600

    @pytest.mark.asyncio
    async def test_set_string_no_serialization(self):
        c = RedisCache()
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        c.redis = mock_redis

        await c.set("key", "plain_string")
        mock_redis.set.assert_called_once_with("key", "plain_string", ex=3600)

    @pytest.mark.asyncio
    async def test_delete_calls_redis(self):
        c = RedisCache()
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock()
        c.redis = mock_redis

        await c.delete("key")
        mock_redis.delete.assert_called_once_with("key")

    @pytest.mark.asyncio
    async def test_exists_calls_redis(self):
        c = RedisCache()
        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)
        c.redis = mock_redis

        assert await c.exists("key") is True

    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        c = RedisCache()
        await c.connect()
        assert c.redis is not None
        await c.disconnect()
