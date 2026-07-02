from collections.abc import AsyncGenerator

from redis.asyncio import Redis, from_url

from app.config.settings import get_settings

settings = get_settings()

_redis_client: Redis | None = None


def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = from_url(settings.redis_url, decode_responses=True)
    return _redis_client


async def get_redis() -> AsyncGenerator[Redis, None]:
    yield get_redis_client()


async def close_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None
