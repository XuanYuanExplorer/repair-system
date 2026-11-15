"""缓存抽象。

默认进程内 TTL 实现（单实例开发/演示零依赖）；
生产通过实现同一接口接入 Redis（`REDIS_URL` 生效时自动切换，见 `build_cache`）。
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Protocol


class CacheBackend(Protocol):
    async def get(self, key: str) -> Any: ...
    async def set(self, key: str, value: Any, ttl: int | None = None) -> None: ...
    async def delete(self, *keys: str) -> None: ...
    async def exists(self, key: str) -> bool: ...
    async def incr(self, key: str, ttl: int | None = None) -> int: ...
    async def ttl(self, key: str) -> int: ...
    async def close(self) -> None: ...


class InMemoryCache:
    """带过期时间的内存缓存，适合单进程部署与测试。"""

    def __init__(self) -> None:
        self._data: dict[str, tuple[Any, float | None]] = {}
        self._lock = asyncio.Lock()

    def _alive(self, key: str) -> bool:
        item = self._data.get(key)
        if not item:
            return False
        _, exp = item
        if exp is not None and exp <= time.time():
            self._data.pop(key, None)
            return False
        return True

    async def get(self, key: str) -> Any:
        async with self._lock:
            if not self._alive(key):
                return None
            return self._data[key][0]

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        async with self._lock:
            self._data[key] = (value, time.time() + ttl if ttl else None)

    async def delete(self, *keys: str) -> None:
        async with self._lock:
            for k in keys:
                self._data.pop(k, None)

    async def exists(self, key: str) -> bool:
        async with self._lock:
            return self._alive(key)

    async def incr(self, key: str, ttl: int | None = None) -> int:
        async with self._lock:
            if not self._alive(key):
                self._data[key] = (1, time.time() + ttl if ttl else None)
                return 1
            value, exp = self._data[key]
            value = int(value) + 1
            self._data[key] = (value, exp)
            return value

    async def ttl(self, key: str) -> int:
        async with self._lock:
            if not self._alive(key):
                return -2
            exp = self._data[key][1]
            return -1 if exp is None else max(0, int(exp - time.time()))

    async def close(self) -> None:
        self._data.clear()


class RedisCache:
    """Redis 适配（redis.asyncio）。仅在配置 REDIS_URL 且已安装 redis 时启用。"""

    def __init__(self, url: str, prefix: str = "dorm") -> None:
        from redis import asyncio as aioredis  # 延迟导入，未安装不影响默认启动

        self._client = aioredis.from_url(url, encoding="utf-8", decode_responses=True)
        self._prefix = prefix

    def _k(self, key: str) -> str:
        return f"{self._prefix}:{key}"

    async def get(self, key: str) -> Any:
        raw = await self._client.get(self._k(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            return raw

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        await self._client.set(self._k(key), json.dumps(value, ensure_ascii=False), ex=ttl)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self._client.delete(*(self._k(k) for k in keys))

    async def exists(self, key: str) -> bool:
        return bool(await self._client.exists(self._k(key)))

    async def incr(self, key: str, ttl: int | None = None) -> int:
        pipe = self._client.pipeline()
        pipe.incr(self._k(key))
        if ttl:
            pipe.expire(self._k(key), ttl, nx=True)
        value, *_ = await pipe.execute()
        return int(value)

    async def ttl(self, key: str) -> int:
        return int(await self._client.ttl(self._k(key)))

    async def close(self) -> None:
        await self._client.aclose()


def build_cache() -> CacheBackend:
    from app.config import settings

    if settings.redis_url:
        try:
            return RedisCache(settings.redis_url, settings.cache_prefix)
        except Exception:  # pragma: no cover - redis 不可用时降级
            pass
    return InMemoryCache()


cache: CacheBackend = build_cache()
