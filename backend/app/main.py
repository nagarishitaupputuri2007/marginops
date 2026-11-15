"""MarginOps FastAPI Application Entrypoint."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.mongo import close_mongo_client
from app.core.redis import close_redis_client
from app.api.v1.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager handling application startup and graceful shutdown."""
    # Startup actions
    yield
    # Shutdown actions: gracefully close asynchronous connection pools
    await close_mongo_client()
    await close_redis_client()


app = FastAPI(
    title="MarginOps API",
    description="AI-powered infrastructure cost intelligence and product economics platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure Cross-Origin Resource Sharing (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Root"])
async def root():
    """Root status endpoint providing API metadata."""
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "docs": "/docs",
        "health": f"{settings.API_V1_PREFIX}/health",
    }
