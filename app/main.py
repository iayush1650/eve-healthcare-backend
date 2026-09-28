"""EVE Healthcare API — Main application entry point."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api import auth, bookings, centres, payments
from app.config import get_settings

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

# ── Structured Logging Setup ────────────────────────────────────────────────

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if get_settings().DEBUG else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(0),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)

# ── Rate Limiter ────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

# ── Lifespan ────────────────────────────────────────────────────────────────

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("app_starting", app_name=settings.APP_NAME)

    # Create all tables (for development convenience)
    from app.database import Base, engine
    import app.models  # noqa: F401 — ensure all models are imported

    Base.metadata.create_all(bind=engine)
    logger.info("database_tables_created")

    # Initialize Redis cache connection
    from app.core.cache import get_redis_client
    redis_client = get_redis_client()
    if redis_client:
        logger.info("redis_cache_connected")
    else:
        logger.warning("redis_cache_unavailable", msg="Running without cache")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("app_shutting_down")


# ── App Factory ─────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Backend service for diagnostic test bookings and simulated payments. "
        "Built for the EVE Healthcare SDE Intern assignment."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── Middleware ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Exception Handlers ──────────────────────────────────────────────────────


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Return structured validation error responses."""
    errors = []
    for error in exc.errors():
        errors.append(
            {
                "field": " -> ".join(str(loc) for loc in error["loc"]),
                "message": error["msg"],
                "type": error["type"],
            }
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
        },
    )


# ── Routes ──────────────────────────────────────────────────────────────────

app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(centres.router, prefix=settings.API_V1_PREFIX)
app.include_router(bookings.router, prefix=settings.API_V1_PREFIX)
app.include_router(payments.router, prefix=settings.API_V1_PREFIX)


# ── Health Check ────────────────────────────────────────────────────────────


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Returns service health status.",
)
def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": settings.APP_NAME, "version": "1.0.0"}


@app.get(
    "/health/cache",
    tags=["Health"],
    summary="Cache health check",
    description="Returns Redis cache connectivity status.",
)
def cache_health_check():
    """Redis cache health check endpoint."""
    from app.core.cache import get_redis_client

    client = get_redis_client()
    if client:
        try:
            info = client.info("memory")
            return {
                "status": "connected",
                "backend": "redis",
                "used_memory_human": info.get("used_memory_human", "unknown"),
            }
        except Exception as e:
            return {"status": "error", "backend": "redis", "error": str(e)}
    return {"status": "unavailable", "backend": "redis", "message": "Redis not connected"}
