"""PostgreSQL Asynchronous Database Module with SQLAlchemy 2.x."""
import asyncio
import time
from typing import AsyncGenerator, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from app.core.config import settings

# Create asynchronous SQLAlchemy engine
engine = create_async_engine(
    settings.async_postgres_url,
    echo=False,
    pool_timeout=2,
    connect_args={"timeout": 1.0},
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_postgres_health() -> Dict[str, Any]:
    """Tests connectivity to PostgreSQL and returns status with roundtrip latency."""
    start_time = time.perf_counter()
    try:
        async def _ping():
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(_ping(), timeout=1.0)
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return {"status": "connected", "latency_ms": latency}
    except Exception as exc:
        return {"status": "unreachable", "error": str(exc)}

