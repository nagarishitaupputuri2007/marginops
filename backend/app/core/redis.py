"""Redis Client Module for Caching and Event Dispatching."""
import asyncio
import time
from typing import Optional, Dict, Any
import redis.asyncio as aioredis
from app.core.config import settings

_redis_client: Optional[aioredis.Redis] = None


def get_redis_client() -> aioredis.Redis:
    """Returns the singleton async Redis client instance."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
    return _redis_client


async def close_redis_client():
    """Closes the async Redis connection."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.aclose()
        _redis_client = None


async def check_redis_health() -> Dict[str, Any]:
    """Tests connectivity to Redis using ping command."""
    start_time = time.perf_counter()
    try:
        async def _ping():
            client = get_redis_client()
            await client.ping()

        await asyncio.wait_for(_ping(), timeout=1.0)
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {"status": "connected", "latency_ms": latency}
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}
