"""
Health check endpoints for monitoring system status.
"""

from datetime import datetime
from typing import Dict, Any
import asyncio
import redis.asyncio as redis
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import structlog

from app.core.settings import settings

logger = structlog.get_logger()
router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    environment: str
    services: Dict[str, Any]


class ServiceStatus(BaseModel):
    """Individual service status model."""
    status: str
    response_time_ms: float
    details: Dict[str, Any] = {}


@router.get("/health", response_model=HealthResponse, summary="Basic health check")
async def health_check():
    """
    Basic health check endpoint.
    Returns the overall system status.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        environment=settings.environment,
        services={}
    )


@router.get("/health/detailed", response_model=HealthResponse, summary="Detailed health check")
async def detailed_health_check():
    """
    Detailed health check that tests external services.
    Returns status of database, Redis, and other dependencies.
    """
    services = {}
    overall_status = "healthy"
    
    # Test Redis connection
    redis_status = await _check_redis()
    services["redis"] = redis_status
    if redis_status.status != "healthy":
        overall_status = "degraded"
    
    # Test database connection (when implemented)
    # db_status = await _check_database()
    # services["database"] = db_status
    # if db_status.status != "healthy":
    #     overall_status = "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow(),
        version=settings.app_version,
        environment=settings.environment,
        services=services
    )


@router.get("/health/readiness", summary="Readiness probe")
async def readiness_check():
    """
    Kubernetes readiness probe.
    Returns 200 if the service is ready to receive traffic.
    """
    try:
        # Test critical services
        redis_status = await _check_redis()
        
        if redis_status.status != "healthy":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready - Redis unavailable"
            )
        
        return {"status": "ready", "timestamp": datetime.utcnow()}
    
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@router.get("/health/liveness", summary="Liveness probe")
async def liveness_check():
    """
    Kubernetes liveness probe.
    Returns 200 if the service is alive (basic functionality).
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow(),
        "uptime": "Service is running"
    }


async def _check_redis() -> ServiceStatus:
    """Test Redis connection and basic operations."""
    start_time = datetime.utcnow()
    
    try:
        # Create Redis client
        redis_client = redis.from_url(settings.redis_url)
        
        # Test basic operations
        await redis_client.ping()
        await redis_client.set("health_check", "test", ex=10)
        result = await redis_client.get("health_check")
        await redis_client.delete("health_check")
        
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        await redis_client.close()
        
        return ServiceStatus(
            status="healthy",
            response_time_ms=response_time,
            details={"connection": "successful", "operations": "working"}
        )
    
    except Exception as e:
        response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        logger.error("Redis health check failed", error=str(e))
        
        return ServiceStatus(
            status="unhealthy",
            response_time_ms=response_time,
            details={"error": str(e)}
        )


# TODO: Implement database health check
# async def _check_database() -> ServiceStatus:
#     """Test database connection and basic operations."""
#     start_time = datetime.utcnow()
#     
#     try:
#         # Test database connection
#         # This will be implemented in Task 1.2
#         
#         response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
#         
#         return ServiceStatus(
#             status="healthy",
#             response_time_ms=response_time,
#             details={"connection": "successful"}
#         )
#     
#     except Exception as e:
#         response_time = (datetime.utcnow() - start_time).total_seconds() * 1000
#         logger.error("Database health check failed", error=str(e))
#         
#         return ServiceStatus(
#             status="unhealthy",
#             response_time_ms=response_time,
#             details={"error": str(e)}
#         ) 