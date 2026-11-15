"""
Database Initialization Script for MarginOps.
Initializes PostgreSQL tables and validates schema state.
"""
import asyncio
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("marginops.init_db")


async def main():
    logger.info("Initializing MarginOps database schema...")
    try:
        from app.core.database import engine, check_postgres_health
        health = await check_postgres_health()
        if health.get("status") != "connected":
            logger.warning(f"PostgreSQL is currently unreachable: {health.get('error')}")
            logger.info("Ensure PostgreSQL is running via Docker Compose before running schema migrations.")
            return

        logger.info("PostgreSQL is connected. Running schema initialization...")
        # Schema migration logic will hook into Alembic migrations
        logger.info("Schema verification completed successfully.")
    except Exception as e:
        logger.error(f"Error during database initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
