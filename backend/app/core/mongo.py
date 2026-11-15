"""MongoDB Module using the Official PyMongo Async API (AsyncMongoClient)."""
import asyncio
import time
from typing import Optional, Dict, Any, List
from pymongo import AsyncMongoClient, ASCENDING, DESCENDING
from pymongo.operations import IndexModel
from app.core.config import settings

TELEMETRY_COLLECTION = "telemetry_events"

_mongo_client: Optional[AsyncMongoClient] = None


def get_mongo_client() -> AsyncMongoClient:
    """Returns the singleton AsyncMongoClient instance."""
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = AsyncMongoClient(
            settings.MONGODB_URL,
            serverSelectionTimeoutMS=2000,
            tz_aware=True,
        )
    return _mongo_client


def get_mongo_db():
    """Returns the primary application database from the async client."""
    client = get_mongo_client()
    return client[settings.MONGODB_DB]


def get_telemetry_index_models() -> List[IndexModel]:
    """Returns the official PyMongo IndexModel definitions for the telemetry collection."""
    return [
        # Primary tenant and time-series compound index
        IndexModel(
            keys=[("organization_id", ASCENDING), ("timestamp", DESCENDING)],
            name="ix_telemetry_org_timestamp",
        ),
        # Tenant, product feature, and time-series compound index (unit economics)
        IndexModel(
            keys=[
                ("organization_id", ASCENDING),
                ("product_feature_id", ASCENDING),
                ("timestamp", DESCENDING),
            ],
            name="ix_telemetry_org_feature_timestamp",
        ),
        # Tenant, event type, and time-series compound index (event categorization)
        IndexModel(
            keys=[
                ("organization_id", ASCENDING),
                ("event_type", ASCENDING),
                ("timestamp", DESCENDING),
            ],
            name="ix_telemetry_org_event_timestamp",
        ),
        # Tenant, provider, AI model, and time-series compound index (model attribution)
        IndexModel(
            keys=[
                ("organization_id", ASCENDING),
                ("provider", ASCENDING),
                ("ai_model", ASCENDING),
                ("timestamp", DESCENDING),
            ],
            name="ix_telemetry_org_provider_model_timestamp",
        ),
        # Distributed trace correlation sparse index
        IndexModel(
            keys=[("trace_id", ASCENDING)],
            name="ix_telemetry_trace_id",
            sparse=True,
        ),
        # Tenant, workload ID, and time-series sparse compound index
        IndexModel(
            keys=[
                ("organization_id", ASCENDING),
                ("workload_id", ASCENDING),
                ("timestamp", DESCENDING),
            ],
            name="ix_telemetry_org_workload_timestamp",
            sparse=True,
        ),
    ]


async def init_telemetry_indexes(db: Optional[Any] = None) -> List[str]:
    """Initializes and ensures compound and sparse indexes on the telemetry collection.

    Uses the official PyMongo Async API (AsyncCollection.create_indexes).

    Args:
        db: Optional AsyncDatabase instance. If None, uses get_mongo_db().

    Returns:
        List of index names successfully created or verified.
    """
    if db is None:
        db = get_mongo_db()
    collection = db[TELEMETRY_COLLECTION]
    indexes = get_telemetry_index_models()
    return await collection.create_indexes(indexes)


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

