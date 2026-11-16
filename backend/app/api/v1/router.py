"""API v1 Central Router Aggregator."""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    anomalies,
    costs,
    forecasting,
    health,
    investigations,
    unit_economics,
)

api_router = APIRouter()

# Mount all domain routers under v1
api_router.include_router(health.router)
api_router.include_router(costs.router)
api_router.include_router(unit_economics.router)
api_router.include_router(anomalies.router)
api_router.include_router(forecasting.router)
api_router.include_router(investigations.router)
