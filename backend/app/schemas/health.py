"""Health check response schemas."""
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field


class DependencyHealth(BaseModel):
    status: str = Field(..., description="Connection status: 'connected' or 'unreachable'")
    latency_ms: Optional[float] = Field(default=None, description="Roundtrip check latency in milliseconds")
    error: Optional[str] = Field(default=None, description="Failure description if unreachable")


class HealthResponse(BaseModel):
    status: str = Field(..., description="Overall status: 'healthy' (all connected) or 'degraded' (one or more down)")
    app: str = Field(..., description="Application name")
    version: str = Field(..., description="Application version")
    environment: str = Field(..., description="Deployment environment")
    timestamp: datetime = Field(..., description="Current server UTC timestamp")
    dependencies: Dict[str, DependencyHealth] = Field(
        ...,
        description="Health status of external backing services (PostgreSQL, MongoDB, Redis)",
    )
