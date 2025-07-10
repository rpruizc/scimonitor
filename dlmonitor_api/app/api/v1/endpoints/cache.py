"""
Cache management endpoints for monitoring and operations.
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
import structlog

from app.core.cache import cache_invalidator, cache_stats, cache_health_check
from app.core.redis import redis_service
from app.api.dependencies.auth import get_current_active_user
from app.models.user import UserModel

logger = structlog.get_logger()
router = APIRouter()


class CacheStatsResponse(BaseModel):
    """Cache statistics response model."""
    cache_counts: Dict[str, int]
    memory_usage: Dict[str, Any]
    connection_stats: Dict[str, Any]
    key_stats: Dict[str, Any]
    uptime_seconds: int
    redis_version: str
    timestamp: str


class CacheKeyInfo(BaseModel):
    """Cache key information model."""
    key: str
    ttl: int
    expires_at: Optional[str]


class CacheHealthResponse(BaseModel):
    """Cache health check response model."""
    status: str
    operations: Dict[str, bool]
    timestamp: str
    error: Optional[str] = None


class CacheInvalidationRequest(BaseModel):
    """Cache invalidation request model."""
    pattern: Optional[str] = None
    content_type: Optional[str] = None
    user_id: Optional[int] = None
    invalidate_all: bool = False


class CacheInvalidationResponse(BaseModel):
    """Cache invalidation response model."""
    success: bool
    keys_invalidated: int
    message: str
    timestamp: str


@router.get("/cache/health", response_model=CacheHealthResponse, summary="Cache health check")
async def cache_health():
    """
    Check cache system health.
    Tests basic Redis operations and connectivity.
    """
    try:
        health_result = await cache_health_check()
        return CacheHealthResponse(**health_result)
    except Exception as e:
        logger.error("Cache health check failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache health check failed"
        )


@router.get("/cache/stats", response_model=CacheStatsResponse, summary="Cache statistics")
async def get_cache_stats():
    """
    Get comprehensive cache statistics.
    Includes memory usage, key counts, and connection stats.
    """
    try:
        stats = await cache_stats.get_cache_stats()
        if "error" in stats:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to get cache stats: {stats['error']}"
            )
        
        return CacheStatsResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get cache stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache statistics"
        )


@router.get("/cache/keys", response_model=List[CacheKeyInfo], summary="Get cache keys")
async def get_cache_keys(
    pattern: str = Query(default="*", description="Key pattern to search for"),
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum number of keys to return")
):
    """
    Get cache keys matching a pattern.
    Useful for debugging and monitoring specific cache entries.
    """
    try:
        keys = await cache_stats.get_cache_keys_by_pattern(pattern, limit)
        return [CacheKeyInfo(**key_info) for key_info in keys]
    except Exception as e:
        logger.error("Failed to get cache keys", pattern=pattern, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache keys"
        )


@router.post("/cache/invalidate", response_model=CacheInvalidationResponse, summary="Invalidate cache")
async def invalidate_cache(
    request: CacheInvalidationRequest,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Invalidate cache entries.
    Supports pattern-based, content-type-based, user-specific, or full cache invalidation.
    
    **Note**: This endpoint requires authentication as it can impact system performance.
    """
    try:
        keys_invalidated = 0
        operation = "none"
        
        if request.invalidate_all:
            keys_invalidated = await cache_invalidator.invalidate_all_cache()
            operation = "invalidate_all"
            logger.warning("All cache invalidated", user_id=current_user.id, count=keys_invalidated)
        
        elif request.pattern:
            keys_invalidated = await cache_invalidator.invalidate_pattern(request.pattern)
            operation = f"pattern:{request.pattern}"
            logger.info("Cache pattern invalidated", user_id=current_user.id, pattern=request.pattern, count=keys_invalidated)
        
        elif request.content_type:
            keys_invalidated = await cache_invalidator.invalidate_content_cache(request.content_type)
            operation = f"content_type:{request.content_type}"
            logger.info("Content cache invalidated", user_id=current_user.id, content_type=request.content_type, count=keys_invalidated)
        
        elif request.user_id:
            keys_invalidated = await cache_invalidator.invalidate_user_cache(request.user_id)
            operation = f"user:{request.user_id}"
            logger.info("User cache invalidated", user_id=current_user.id, target_user_id=request.user_id, count=keys_invalidated)
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify one of: pattern, content_type, user_id, or invalidate_all"
            )
        
        return CacheInvalidationResponse(
            success=True,
            keys_invalidated=keys_invalidated,
            message=f"Successfully invalidated {keys_invalidated} cache entries ({operation})",
            timestamp=datetime.utcnow().isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Cache invalidation failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache invalidation failed"
        )


@router.get("/cache/key/{key}", summary="Get cache key value")
async def get_cache_key(
    key: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get the value of a specific cache key.
    Useful for debugging and inspecting cache contents.
    """
    try:
        value = await redis_service.get(key)
        ttl = await redis_service.ttl(key)
        
        return {
            "key": key,
            "value": value,
            "ttl": ttl,
            "expires_at": (datetime.utcnow().timestamp() + ttl) if ttl > 0 else None,
            "exists": value is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Failed to get cache key", key=key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve cache key"
        )


@router.delete("/cache/key/{key}", summary="Delete cache key")
async def delete_cache_key(
    key: str,
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Delete a specific cache key.
    """
    try:
        deleted = await redis_service.delete(key)
        
        if deleted:
            logger.info("Cache key deleted", key=key, user_id=current_user.id)
            return {
                "success": True,
                "message": f"Cache key '{key}' deleted successfully",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "message": f"Cache key '{key}' not found",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    except Exception as e:
        logger.error("Failed to delete cache key", key=key, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete cache key"
        )


@router.post("/cache/warm", summary="Warm cache")
async def warm_cache_endpoint(
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Warm cache by preloading frequently accessed data.
    This endpoint triggers cache warming for common queries.
    """
    try:
        # This could be expanded to warm specific cache entries
        # For now, it's a placeholder that could trigger background tasks
        
        logger.info("Cache warming initiated", user_id=current_user.id)
        
        return {
            "success": True,
            "message": "Cache warming initiated",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error("Cache warming failed", user_id=current_user.id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cache warming failed"
        )


# Public endpoint for basic cache information (no auth required)
@router.get("/cache/info", summary="Basic cache information")
async def get_cache_info():
    """
    Get basic cache information without sensitive details.
    This endpoint is public and can be used for monitoring.
    """
    try:
        # Get basic stats without sensitive information
        stats = await cache_stats.get_cache_stats()
        
        if "error" in stats:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Cache service unavailable"
            )
        
        # Return only basic information
        return {
            "status": "healthy",
            "total_keys": stats.get("key_stats", {}).get("total_keys", 0),
            "memory_usage": stats.get("memory_usage", {}).get("used_memory_human", "0B"),
            "redis_version": stats.get("redis_version", "unknown"),
            "uptime_seconds": stats.get("uptime_seconds", 0),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get cache info", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache service unavailable"
        ) 