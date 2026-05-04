"""FastAPI application entry point for FoundrAI backend."""

import logging
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
from backend.storage.supabase_client import get_supabase_client

settings = get_settings()

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    import asyncio
    from backend.rag.encoder import get_encoder
    logger.info("FoundrAI backend starting — environment: %s", settings.environment)
    get_supabase_client()  # warm DB connection
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, get_encoder)  # pre-load ONNX embedding model off the event loop
    logger.info("Embedding model ready")
    yield
    logger.info("FoundrAI backend shutting down")


app = FastAPI(
    title="FoundrAI API",
    description="Autonomous AI advisory platform for startup founders",
    version="1.0.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_allow_origin_regex or None,
    allow_credentials=False,  # Frontend uses Authorization: Bearer — cookies not needed
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["Content-Type", "X-Total-Count"],  # expose_headers required for SSE EventSource
    max_age=600,
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, str(exc))
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {"code": "INTERNAL_ERROR", "message": "An unexpected error occurred"},
        },
    )


app.include_router(auth_router)
app.include_router(upload_router)
app.include_router(query_router)
app.include_router(simulate_router)
app.include_router(charts_router)
app.include_router(founders_router)


@app.api_route("/health", methods=["GET", "HEAD"], tags=["health"])
async def health() -> dict:
    return {"status": "ok", "version": "1.0.0", "environment": settings.environment}
