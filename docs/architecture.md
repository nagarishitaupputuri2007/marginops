# MarginOps Architecture Specification

MarginOps is an AI-powered infrastructure cost intelligence and product economics platform built as a high-performance modular monolith with asynchronous background workers.

## 1. System Architecture Overview

```
                                +---------------------------+
                                |      React Frontend       |
                                | (TypeScript + Vite + TW4) |
                                +-------------+-------------+
                                              |
                                     REST API / JSON
                                              |
                                              v
                                +---------------------------+
                                |      FastAPI Backend      |
                                |     (Modular Monolith)    |
                                +-----+---------------+-----+
                                      |               |
                +---------------------+               +---------------------+
                |                     |                                     |
                v                     v                                     v
     +--------------------+ +--------------------+                +--------------------+
     |     PostgreSQL     | |      MongoDB       |                |       Redis        |
     | (Relational/Ledger)| |(Telemetry & Events)|                | (Cache & Message)  |
     +--------------------+ +--------------------+                +---------+----------+
                                                                            |
                                                                            v
                                                                  +--------------------+
                                                                  |   Celery Workers   |
                                                                  |  (Async Execution) |
                                                                  +--------------------+
```

## 2. Core Components & Responsibilities

### Frontend
- **Framework**: React with TypeScript and Vite.
- **Styling**: Tailwind CSS 4 utilizing `@tailwindcss/vite` without legacy PostCSS overhead.
- **State & Networking**: TanStack Query for server state management and caching; Axios for typed HTTP communication with the backend.
- **Routing**: React Router with declarative layouts.

### Backend (Modular Monolith)
- **Framework**: FastAPI (ASGI) with Pydantic v2 validation and typed `pydantic-settings`.
- **Relational Storage (PostgreSQL)**:
  - Stores structured financial records, user accounts, tenant configurations, pricing catalogs, and allocation models.
  - Accessed via SQLAlchemy 2.x asynchronous engine with `asyncpg`.
  - Schema migrations managed by Alembic.
- **Telemetry & Event Ingestion (MongoDB)**:
  - Stores high-volume, semi-structured infrastructure usage logs, cloud bill line items (AWS CUR, GCP billing export), and container resource metrics.
  - Accessed via the official **PyMongo Async API** (`AsyncMongoClient`). Motor is omitted in favor of the official async driver.
- **Cache & Message Broker (Redis)**:
  - High-speed query caching and session state.
  - Celery message broker and result backend.
- **Asynchronous Task Processing (Celery)**:
  - Offloads long-running cost aggregation, cloud billing ingestion, and economic forecasting from the main request/response cycle.
  - Configured for worker execution via Docker containers (or `--pool=solo` for standalone Windows testing).

## 3. Modularity Boundaries
- `app/core`: Shared system infrastructure, configuration, and database connection pools.
- `app/api/v1`: Endpoint definitions and routing.
- `app/schemas`: Pydantic request/response transfer objects.
- `app/models`: Relational database schemas and Mongo document structures.
- `app/services`: Pure domain business logic.
- `app/workers`: Background worker tasks and Celery task definitions.

## 4. Health & Observability Strategy
- The platform implements a multi-tier health check at `/api/v1/health`.
- Distinguishes application process viability from external service availability.
- The API server initializes safely even if one or more downstream databases are temporarily down, accurately reporting connectivity status per subsystem (`postgres`, `mongodb`, `redis`).
