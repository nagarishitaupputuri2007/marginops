"""MongoDB Module using the Official PyMongo Async API (AsyncMongoClient)."""
import asyncio
import time
from typing import Optional, Dict, Any
from pymongo import AsyncMongoClient
from app.core.config import settings

_mongo_client: Optional[AsyncMongoClient] = None


def get_mongo_client() -> AsyncMongoClient:
    """Returns the singleton AsyncMongoClient instance."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncMongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=2000,
        )
    return _mongo_client


def get_mongo_db():
    """Returns the primary application database from the async client."""
    client = get_mongo_client()
    return client[settings.MONGODB_DB]


async def close_mongo_client():
    """Closes the async mongo client connection pool."""
    global _mongo_client
    if _mongo_client is not None:
        await _mongo_client.close()
        _mongo_client = None


async def check_mongo_health() -> Dict[str, Any]:
    """Tests connectivity to MongoDB using admin ping command."""
    start_time = time.perf_counter()
    try:
        async def _ping():
            client = get_mongo_client()
            await client.admin.command("ping")

        await asyncio.wait_for(_ping(), timeout=1.0)
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {"status": "connected", "latency_ms": latency}
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}
