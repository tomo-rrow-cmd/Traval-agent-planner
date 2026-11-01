"""
Redis 缓存工具 - 封装 Redis 操作
"""

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import settings


class RedisCache:
    """Redis 缓存客户端"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """建立 Redis 连接"""
        self.redis = await aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )

    async def disconnect(self):
        """关闭 Redis 连接"""
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.redis:
            return None
        value = await self.redis.get(key)
        if value:
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value
        return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600,
    ) -> None:
        """设置缓存值"""
        if not self.redis:
            return
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False)
        await self.redis.set(key, value, ex=expire)

    async def delete(self, key: str) -> None:
        """删除缓存"""
        if self.redis:
            await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.redis:
            return False
        return await self.redis.exists(key) > 0


# 全局缓存实例
cache = RedisCache()
