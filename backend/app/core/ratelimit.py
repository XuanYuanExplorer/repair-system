"""限流与冷却：Redis 令牌桶的轻量替代（固定窗口计数）。"""
from app.core.cache import cache
from app.core.errors import BizError, ErrCode


async def hit(key: str, limit: int, window: int = 60, message: str | None = None) -> int:
    count = await cache.incr(f"rate:{key}", ttl=window)
    if count > limit:
        ttl = await cache.ttl(f"rate:{key}")
        raise BizError(ErrCode.RATE_LIMITED, message, data={"retry_after": max(ttl, 1)})
    return count


async def ensure_cooldown(key: str) -> None:
    """若处于冷却期则抛 429。"""
    left = await cache.ttl(f"cool:{key}")
    if left > 0:
        raise BizError(ErrCode.RATE_LIMITED, "操作太频繁，请稍后再试", data={"retry_after": left})


async def set_cooldown(key: str, seconds: int) -> None:
    await cache.set(f"cool:{key}", 1, ttl=seconds)


async def cooldown_left(key: str) -> int:
    return max(await cache.ttl(f"cool:{key}"), 0)


async def bump_daily(key: str, limit: int) -> int:
    count = await cache.incr(f"daily:{key}", ttl=86400)
    if count > limit:
        raise BizError(ErrCode.RATE_LIMITED, "今日次数已用尽，请明日再试", data={"retry_after": 86400})
    return count
