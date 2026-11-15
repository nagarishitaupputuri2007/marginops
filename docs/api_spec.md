# MarginOps API Specification (v1 Foundation)

Base URL: `/api/v1`

## Health Probe Endpoint

### `GET /api/v1/health`
Returns the operational status of the MarginOps backend and reports connectivity to backing infrastructure components (PostgreSQL, MongoDB, and Redis).

#### Response (200 OK)
```json
{
  "status": "healthy",
  "app": "marginops-backend",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-11-15T10:45:00.000Z",
  "dependencies": {
    "postgres": {
      "status": "connected",
      "latency_ms": 1.2
    },
    "mongodb": {
      "status": "connected",
      "latency_ms": 2.1
    },
    "redis": {
      "status": "connected",
      "latency_ms": 0.8
    }
  }
}
```

#### Degraded Response (200 OK)
If any dependency is unreachable, the API continues operating and responds with `status: "degraded"`, identifying the unreachable service.
```json
{
  "status": "degraded",
  "app": "marginops-backend",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": "2026-11-15T10:45:00.000Z",
  "dependencies": {
    "postgres": {
      "status": "unreachable",
      "error": "Connection refused"
    },
    "mongodb": {
      "status": "unreachable",
      "error": "Server selection timed out"
    },
    "redis": {
      "status": "unreachable",
      "error": "Connection refused"
    }
  }
}
```
