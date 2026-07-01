"""
Main entrypoint for the OmniShop TMA FastAPI Backend.
Defines application lifecycle, middleware, CORS, rate limiting, and mounts routers.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import engine, Base
from app.middleware.correlation_id import CorrelationIdFilter, CorrelationIdMiddleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.api.v1.router import router as api_v1_router
from app.services import storage

# Configure structured logging with correlation ID support
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s [cid=%(correlation_id)s]: %(message)s",
)
_cid_filter = CorrelationIdFilter()
for _handler in logging.getLogger().handlers:
    _handler.addFilter(_cid_filter)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for database connections and pre-warming."""
    logger.info("Initializing OmniShop TMA API Server...")
    
    # ── Self-healing database migration runner ────────────────────────────────
    try:
        import subprocess
        import sys
        logger.info("Running database migrations via Alembic...")
        res = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True
        )
        if res.returncode != 0:
            err_msg = res.stderr or res.stdout
            if "already exists" in err_msg or "DuplicateTable" in err_msg:
                logger.info("Baseline tables detected in database. Stamping baseline '0001_baseline'...")
                stamp_res = subprocess.run(
                    [sys.executable, "-m", "alembic", "stamp", "0001_baseline"],
                    capture_output=True,
                    text=True
                )
                if stamp_res.returncode == 0:
                    logger.info("Baseline stamped successfully. Applying pending migrations...")
                    subprocess.run(
                        [sys.executable, "-m", "alembic", "upgrade", "head"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    logger.info("Database migrations completed successfully after stamping.")
                else:
                    logger.error("Failed to stamp baseline: %s", stamp_res.stderr)
            else:
                logger.error("Database migration failed: %s", err_msg)
        else:
            logger.info("Database migrations completed successfully.")
    except Exception as exc:
        logger.error("Database migration runner encountered an error: %s", exc)

    settings = get_settings()
    
    # In development mode, auto-generate tables if needed
    if settings.ENVIRONMENT == "development":
        logger.info("Development environment detected: checking database tables...")
        try:
            async with engine.begin() as conn:
                # This ensures tables are created if not exist, though Alembic is primary
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables verified.")
        except Exception as exc:
            logger.error("Error creating database tables at startup: %s", exc)
            
    yield
    
    logger.info("Shutting down OmniShop TMA API Server...")
    await engine.dispose()
    logger.info("Database connections closed.")


# Create FastAPI application
app = FastAPI(
    title="OmniShop TMA API",
    description="High-performance backend for single-seller Telegram Mini App and Webhook Automation.",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()

# Correlation ID must wrap everything so the ID is available during rate limiting.
app.add_middleware(CorrelationIdMiddleware)

# Rate Limiter middleware
app.add_middleware(RateLimiterMiddleware)

# CORS configuration — include all common local dev ports
frontend_url = settings.FRONTEND_URL.strip()
origins = [
    frontend_url,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
    "http://localhost:3002",
    "http://127.0.0.1:3002",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_v1_router, prefix="/api/v1")

# Serve locally-stored uploads when no remote provider (e.g. Cloudinary) is set.
# In production CLOUDINARY_URL is configured, so this mount is skipped and images
# are served from the Cloudinary CDN instead.
if not storage.is_remote():
    upload_path = Path(settings.UPLOAD_DIR)
    upload_path.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=upload_path), name="uploads")


@app.get("/health", tags=["System"])
async def health_check():
    """Simple status check for container deployment probes."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "0.1.0",
    }


@app.get("/", tags=["System"])
async def root():
    """Root metadata details."""
    return {
        "name": "OmniShop TMA Backend",
        "docs_url": "/docs",
        "health_check_url": "/health",
        "status": "online",
    }