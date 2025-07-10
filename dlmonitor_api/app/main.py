"""
Main FastAPI application for DLMonitor API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import structlog

from app.core.settings import settings
from app.api.v1.endpoints import health, papers, tweets, search, users, auth_test
from app.db.base import create_tables, close_engine

# Import models to ensure they're registered with SQLAlchemy
from app.models import ArxivModel, TwitterModel, WorkingQueueModel, UserModel


# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    Handles startup and shutdown tasks.
    """
    # Startup
    logger.info("Starting DLMonitor API", version=settings.app_version, environment=settings.environment)
    
    # Initialize Sentry for error tracking in production
    if settings.sentry_dsn and settings.sentry_dsn.strip() and settings.sentry_dsn.startswith("https://"):
        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            
            sentry_sdk.init(
                dsn=settings.sentry_dsn,
                integrations=[FastApiIntegration()],
                traces_sample_rate=0.1 if settings.is_production else 1.0,
                environment=settings.environment,
            )
            logger.info("Sentry initialized for error tracking")
        except Exception as e:
            logger.warning("Failed to initialize Sentry", error=str(e))
    else:
        logger.debug("Sentry disabled - no valid DSN provided")
    
    # Initialize database tables
    try:
        await create_tables()
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize database tables", error=str(e))
        # Don't fail startup - let health checks report database issues
    
    yield
    
    # Shutdown
    logger.info("Shutting down DLMonitor API")
    
    # Close database connections
    try:
        await close_engine()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error("Error closing database connections", error=str(e))


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Modern API for monitoring deep learning research papers, tweets, and discussions",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )
    
    # Security middleware
    if settings.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["dlmonitor.com", "*.dlmonitor.com", "localhost"]
        )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=settings.allowed_methods,
        allow_headers=settings.allowed_headers,
    )
    
    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(papers.router, prefix="/api/v1", tags=["Papers"])
    app.include_router(tweets.router, prefix="/api/v1", tags=["Tweets"])
    app.include_router(search.router, prefix="/api/v1", tags=["Search"])
    app.include_router(users.router, prefix="/api/v1", tags=["Users"])
    app.include_router(auth_test.router, prefix="/api/v1", tags=["Auth Testing"])
    
    return app


# Create the FastAPI application instance
app = create_application()


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "Welcome to DLMonitor API",
        "version": settings.app_version,
        "environment": settings.environment,
        "docs_url": "/docs" if not settings.is_production else "Documentation disabled in production",
        "database": "SQLAlchemy 2.0 with async support",
        "authentication": "Supabase Auth with JWT tokens",
        "models": ["ArxivModel", "TwitterModel", "WorkingQueueModel", "UserModel"],
    } 