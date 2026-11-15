"""Health check endpoint evaluating application and infrastructure connectivity."""
import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter
from app.core.config import settings
from app.core.database import check_postgres_health
from app.core.mongo import check_mongo_health
from app.core.redis import check_redis_health
from app.schemas.health import HealthResponse, DependencyHealth

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["Health"])
async def get_health() -> HealthResponse:
    """
    Evaluates backend application health and backing service connectivity.
    The endpoint remains responsive with HTTP 200 even if dependencies are offline,
    marking overall status as 'degraded' when one or more services are unreachable.
    """
    # Execute health checks concurrently with timeouts
    postgres_res, mongo_res, redis_res = await asyncio.gather(
        check_postgres_health(),
        check_mongo_health(),
        check_redis_health(),
        return_exceptions=True,
    )

    def parse_result(result) -> DependencyHealth:
        if isinstance(result, Exception):
            return DependencyHealth(status="unreachable", error=str(result))
        if isinstance(result, dict):
            return DependencyHealth(
                status=result.get("status", "unreachable"),
                latency_ms=result.get("latency_ms"),
                error=result.get("error"),
            )
        return DependencyHealth(status="unreachable", error="Unknown check result")

    dependencies = {
        "postgres": parse_result(postgres_res),
        "mongodb": parse_result(mongo_res),
        "redis": parse_result(redis_res),
    }

    all_connected = all(dep.status == "connected" for dep in dependencies.values())
    overall_status = "healthy" if all_connected else "degraded"

    return HealthResponse(
        status=overall_status,
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
        dependencies=dependencies,
    )
