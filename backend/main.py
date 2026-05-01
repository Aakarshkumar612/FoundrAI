"""FastAPI application entry point for FoundrAI backend."""

import logging
import logging.config
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.config import get_settings
from backend.auth.router import router as auth_router
from backend.routers.upload import router as upload_router
from backend.routers.query import router as query_router
from backend.routers.simulate import router as simulate_router
from backend.routers.charts import router as charts_router
from backend.routers.founders import router as founders_router
from backend.news.scheduler import start_scheduler, stop_scheduler
from backend.storage.supabase_client import get_supabase_client

settings = get_settings()

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup and shutdown logic around the app lifecycle."""
    logger.info("FoundrAI backend starting — environment: %s", settings.environment)

    if settings.newscatcher_api_key:
        sb = get_supabase_client()
        start_scheduler(api_key=settings.newscatcher_api_key, supabase_client=sb)
    else:
        logger.warning("NEWSCATCHER_API_KEY not set — news scheduler disabled")

    # Warm Supabase connection on startup so first request isn't cold
    get_supabase_client()

    yield

    stop_scheduler()
    logger.info("FoundrAI backend shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="FoundrAI API",
    description="Autonomous AI advisory platform for startup founders",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global exception handler ──────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert unhandled exceptions into a consistent error envelope."""
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        },
    )

# ── Routers ───────────────────────────────────────────────────────────────────

app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(simulate_router)
app.include_router(charts_router)
app.include_router(founders_router)

# ── Health check ──────────────────────────────────────────────────────────────

@app.get("/health", tags=["health"])
async def health() -> dict:
    """Liveness probe — no auth required."""
    return {"status": "ok", "version": "1.0.0", "environment": settings.environment}
