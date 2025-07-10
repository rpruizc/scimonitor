"""
Caching decorators and utilities for API responses.
Implements cache invalidation strategies and performance optimization.
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable, Union
from functools import wraps
import asyncio
import structlog

from app.core.redis import redis_service

logger = structlog.get_logger()


class CacheConfig:
    """Configuration for different cache types."""
    
    # Default cache TTL values (in seconds)
    DEFAULT_TTL = 300  # 5 minutes
    SHORT_TTL = 60     # 1 minute
    MEDIUM_TTL = 900   # 15 minutes
    LONG_TTL = 3600    # 1 hour
    VERY_LONG_TTL = 86400  # 24 hours
    
    # Cache key prefixes
    API_CACHE_PREFIX = "api_cache:"
    SEARCH_CACHE_PREFIX = "search_cache:"
    USER_CACHE_PREFIX = "user_cache:"
    PAPER_CACHE_PREFIX = "paper_cache:"
    TWEET_CACHE_PREFIX = "tweet_cache:"
    
    # Cache invalidation patterns
    INVALIDATION_PATTERNS = {
        "papers": ["api_cache:papers:*", "search_cache:*"],
        "tweets": ["api_cache:tweets:*", "search_cache:*"],
        "users": ["api_cache:users:*", "user_cache:*"],
        "search": ["search_cache:*"],
    }


def _generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.
    
    Args:
        prefix: Cache key prefix
        *args: Function positional arguments
        **kwargs: Function keyword arguments
        
    Returns:
        Generated cache key
    """
    # Create a hashable representation of the arguments
    key_data = {
        "args": args,
        "kwargs": {k: v for k, v in kwargs.items() if k not in ['session', 'current_user']}
    }
    
    # Serialize and hash the data
    key_string = json.dumps(key_data, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_string.encode()).hexdigest()
    
    return f"{prefix}{key_hash}"


def cache_response(
    ttl: int = CacheConfig.DEFAULT_TTL,
    prefix: str = CacheConfig.API_CACHE_PREFIX,
    vary_on_user: bool = False,
    cache_null: bool = False,
    cache_exceptions: bool = False
):
    """
    Decorator to cache API response data.
    
    Args:
        ttl: Time to live in seconds
        prefix: Cache key prefix
        vary_on_user: Include user ID in cache key
        cache_null: Cache null/None responses
        cache_exceptions: Cache exception responses
        
    Usage:
        @cache_response(ttl=300, prefix="papers:")
        async def get_papers():
            return await fetch_papers()
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key_args = list(args)
            cache_key_kwargs = dict(kwargs)
            
            # Include user ID if requested
            if vary_on_user and 'current_user' in kwargs:
                user = kwargs['current_user']
                cache_key_kwargs['_user_id'] = user.id if hasattr(user, 'id') else str(user)
            
            cache_key = _generate_cache_key(prefix, *cache_key_args, **cache_key_kwargs)
            
            # Try to get from cache
            try:
                cached_result = await redis_service.get(cache_key)
                if cached_result is not None:
                    logger.debug("Cache hit", cache_key=cache_key, function=func.__name__)
                    return cached_result
            except Exception as e:
                logger.warning("Cache read failed", cache_key=cache_key, error=str(e))
            
            # Cache miss - execute function
            try:
                result = await func(*args, **kwargs)
                
                # Cache the result
                should_cache = True
                if result is None and not cache_null:
                    should_cache = False
                
                if should_cache:
                    try:
                        await redis_service.set(cache_key, result, ttl)
                        logger.debug("Cache stored", cache_key=cache_key, function=func.__name__)
                    except Exception as e:
                        logger.warning("Cache write failed", cache_key=cache_key, error=str(e))
                
                return result
                
            except Exception as e:
                if cache_exceptions:
                    error_result = {"error": str(e), "cached_at": datetime.utcnow().isoformat()}
                    try:
                        await redis_service.set(cache_key, error_result, min(ttl, 60))  # Cache errors for shorter time
                    except:
                        pass
                raise
        
        return wrapper
    return decorator


def cache_user_data(ttl: int = CacheConfig.MEDIUM_TTL):
    """
    Decorator specifically for user-related data caching.
    Automatically varies on user ID.
    """
    return cache_response(
        ttl=ttl,
        prefix=CacheConfig.USER_CACHE_PREFIX,
        vary_on_user=True,
        cache_null=False
    )


def cache_search_results(ttl: int = CacheConfig.SHORT_TTL):
    """
    Decorator for caching search results.
    Short TTL since search results can change frequently.
    """
    return cache_response(
        ttl=ttl,
        prefix=CacheConfig.SEARCH_CACHE_PREFIX,
        vary_on_user=False,
        cache_null=True
    )


def cache_static_data(ttl: int = CacheConfig.LONG_TTL):
    """
    Decorator for caching static/rarely changing data.
    Long TTL for data that doesn't change often.
    """
    return cache_response(
        ttl=ttl,
        prefix=CacheConfig.API_CACHE_PREFIX,
        vary_on_user=False,
        cache_null=True
    )


class CacheInvalidator:
    """
    Handles cache invalidation strategies.
    """
    
    def __init__(self, redis_service):
        self.redis = redis_service
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "api_cache:papers:*")
            
        Returns:
            Number of keys invalidated
        """
        try:
            count = await self.redis.flush_pattern(pattern)
            if count > 0:
                logger.info("Cache invalidated", pattern=pattern, count=count)
            return count
        except Exception as e:
            logger.error("Cache invalidation failed", pattern=pattern, error=str(e))
            return 0
    
    async def invalidate_key(self, key: str) -> bool:
        """
        Invalidate a specific cache key.
        
        Args:
            key: Cache key to invalidate
            
        Returns:
            True if key was invalidated, False otherwise
        """
        try:
            result = await self.redis.delete(key)
            if result:
                logger.info("Cache key invalidated", key=key)
            return result
        except Exception as e:
            logger.error("Cache key invalidation failed", key=key, error=str(e))
            return False
    
    async def invalidate_user_cache(self, user_id: int) -> int:
        """
        Invalidate all cache entries for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            Number of keys invalidated
        """
        patterns = [
            f"{CacheConfig.USER_CACHE_PREFIX}*_user_id*{user_id}*",
            f"{CacheConfig.API_CACHE_PREFIX}*_user_id*{user_id}*"
        ]
        
        total_invalidated = 0
        for pattern in patterns:
            count = await self.invalidate_pattern(pattern)
            total_invalidated += count
        
        return total_invalidated
    
    async def invalidate_content_cache(self, content_type: str) -> int:
        """
        Invalidate cache for a specific content type.
        
        Args:
            content_type: Content type (papers, tweets, users, search)
            
        Returns:
            Number of keys invalidated
        """
        patterns = CacheConfig.INVALIDATION_PATTERNS.get(content_type, [])
        
        total_invalidated = 0
        for pattern in patterns:
            count = await self.invalidate_pattern(pattern)
            total_invalidated += count
        
        return total_invalidated
    
    async def invalidate_all_cache(self) -> int:
        """
        Invalidate all application cache.
        Use with caution - only for maintenance or major data updates.
        
        Returns:
            Number of keys invalidated
        """
        patterns = [
            f"{CacheConfig.API_CACHE_PREFIX}*",
            f"{CacheConfig.SEARCH_CACHE_PREFIX}*",
            f"{CacheConfig.USER_CACHE_PREFIX}*",
            f"{CacheConfig.PAPER_CACHE_PREFIX}*",
            f"{CacheConfig.TWEET_CACHE_PREFIX}*"
        ]
        
        total_invalidated = 0
        for pattern in patterns:
            count = await self.invalidate_pattern(pattern)
            total_invalidated += count
        
        logger.warning("All cache invalidated", count=total_invalidated)
        return total_invalidated


# Global cache invalidator
cache_invalidator = CacheInvalidator(redis_service)


class CacheStats:
    """
    Cache statistics and monitoring.
    """
    
    def __init__(self, redis_service):
        self.redis = redis_service
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            # Get basic Redis info
            client = await self.redis._get_client()
            info = await client.info()
            
            # Count cache keys by type
            cache_counts = {}
            for prefix in ["api_cache:", "search_cache:", "user_cache:", "paper_cache:", "tweet_cache:"]:
                keys = await self.redis.keys(f"{prefix}*")
                cache_counts[prefix.rstrip(":")] = len(keys)
            
            # Memory usage
            memory_usage = {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "used_memory_peak": info.get("used_memory_peak", 0),
                "used_memory_peak_human": info.get("used_memory_peak_human", "0B"),
            }
            
            # Connection stats
            connection_stats = {
                "connected_clients": info.get("connected_clients", 0),
                "blocked_clients": info.get("blocked_clients", 0),
                "total_connections_received": info.get("total_connections_received", 0),
            }
            
            # Key statistics
            key_stats = {
                "total_keys": sum(cache_counts.values()),
                "expired_keys": info.get("expired_keys", 0),
                "evicted_keys": info.get("evicted_keys", 0),
            }
            
            return {
                "cache_counts": cache_counts,
                "memory_usage": memory_usage,
                "connection_stats": connection_stats,
                "key_stats": key_stats,
                "uptime_seconds": info.get("uptime_in_seconds", 0),
                "redis_version": info.get("redis_version", "unknown"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to get cache stats", error=str(e))
            return {"error": str(e)}
    
    async def get_cache_keys_by_pattern(self, pattern: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get cache keys matching a pattern with their TTL.
        
        Args:
            pattern: Redis key pattern
            limit: Maximum number of keys to return
            
        Returns:
            List of keys with metadata
        """
        try:
            keys = await self.redis.keys(pattern)
            if not keys:
                return []
            
            # Limit the number of keys to avoid performance issues
            keys = keys[:limit]
            
            key_info = []
            for key in keys:
                ttl = await self.redis.ttl(key)
                key_info.append({
                    "key": key,
                    "ttl": ttl,
                    "expires_at": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat() if ttl > 0 else None
                })
            
            return key_info
            
        except Exception as e:
            logger.error("Failed to get cache keys", pattern=pattern, error=str(e))
            return []


# Global cache stats
cache_stats = CacheStats(redis_service)


# Convenience functions for common cache operations
async def warm_cache(func: Callable, *args, **kwargs) -> Any:
    """
    Warm cache by executing a function.
    Useful for preloading frequently accessed data.
    """
    try:
        result = await func(*args, **kwargs)
        logger.info("Cache warmed", function=func.__name__)
        return result
    except Exception as e:
        logger.error("Cache warming failed", function=func.__name__, error=str(e))
        raise


async def cache_health_check() -> Dict[str, Any]:
    """
    Health check for cache system.
    
    Returns:
        Dictionary with health status
    """
    try:
        # Test basic Redis operations
        test_key = "health_check_cache"
        test_value = {"timestamp": datetime.utcnow().isoformat(), "test": True}
        
        # Test set/get/delete
        await redis_service.set(test_key, test_value, 10)
        retrieved_value = await redis_service.get(test_key)
        await redis_service.delete(test_key)
        
        return {
            "status": "healthy",
            "operations": {
                "set": True,
                "get": retrieved_value == test_value,
                "delete": True
            },
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        } 