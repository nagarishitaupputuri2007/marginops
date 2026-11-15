"""Tests for API health monitoring and dependency isolation."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Verifies root endpoint returns service metadata."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "marginops-backend"
    assert data["status"] == "operational"
    assert "health" in data


@pytest.mark.asyncio
async def test_health_endpoint_contract(async_client: AsyncClient):
    """
    Verifies /api/v1/health returns 200 and strictly adheres to the HealthResponse contract,
    even when background infrastructure services are offline.
    """
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["healthy", "degraded"]
    assert data["app"] == "marginops-backend"
    assert data["version"] == "0.1.0"
    assert "environment" in data
    assert "timestamp" in data
    assert "dependencies" in data

    dependencies = data["dependencies"]
    for service_name in ["postgres", "mongodb", "redis"]:
        assert service_name in dependencies
        dep_data = dependencies[service_name]
        assert dep_data["status"] in ["connected", "unreachable"]
        if dep_data["status"] == "unreachable":
            assert "error" in dep_data


@pytest.mark.asyncio
async def test_health_all_connected_mock(async_client: AsyncClient, monkeypatch):
    """Verifies that when all backing services respond, overall status is 'healthy'."""
    async def mock_connected():
        return {"status": "connected", "latency_ms": 1.5}

    monkeypatch.setattr("app.api.v1.endpoints.health.check_postgres_health", mock_connected)
    monkeypatch.setattr("app.api.v1.endpoints.health.check_mongo_health", mock_connected)
    monkeypatch.setattr("app.api.v1.endpoints.health.check_redis_health", mock_connected)

    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["dependencies"]["postgres"]["status"] == "connected"
    assert data["dependencies"]["mongodb"]["status"] == "connected"
    assert data["dependencies"]["redis"]["status"] == "connected"
