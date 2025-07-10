"""
Redis service layer for DLMonitor API.
Handles connection management, session storage, and caching operations.
"""

import json
import pickle
from datetime import datetime, timedelta
from typing import Optional, Any, Dict, List, Union
from functools import wraps
import asyncio
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool
import structlog

from app.core.settings import settings

logger = structlog.get_logger()

# Global Redis client instance
_redis_client: Optional[redis.Redis] = None
_redis_pool: Optional[ConnectionPool] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client instance with connection pooling.
    """
    global _redis_client, _redis_pool
    
    if _redis_client is None:
        try:
            # Create connection pool
            _redis_pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
            
            # Create Redis client
            _redis_client = redis.Redis(connection_pool=_redis_pool)
            
            # Test connection
            await _redis_client.ping()
            logger.info("Redis client initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize Redis client", error=str(e))
            raise
    
    return _redis_client


async def close_redis_client():
    """Close Redis client and connection pool."""
    global _redis_client, _redis_pool
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
    
    logger.info("Redis client closed")


class RedisService:
    """
    Redis service class for centralized Redis operations.
    """
    
    def __init__(self):
        self.client = None
    
    async def _get_client(self) -> redis.Redis:
        """Get Redis client instance."""
        if self.client is None:
            self.client = await get_redis_client()
        return self.client
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """
        Set a value in Redis with optional expiration.
        
        Args:
            key: Redis key
            value: Value to store (will be serialized)
            expire: Expiration time in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            client = await self._get_client()
            
            # Serialize value with metadata to know how to deserialize
            if isinstance(value, (dict, list)):
                # Use JSON for dict/list with prefix
                serialized_value = "json:" + json.dumps(value)
            elif isinstance(value, str):
                # Use string with prefix
                serialized_value = "str:" + value
            else:
                # Use pickle for other types with prefix
                pickled_data = pickle.dumps(value)
                serialized_value = b"pickle:" + pickled_data
            
            # Set value with optional expiration
            if expire:
                await client.setex(key, expire, serialized_value)
            else:
                await client.set(key, serialized_value)
            
            return True
            
        except Exception as e:
            logger.error("Redis set operation failed", key=key, error=str(e))
            return False
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key
            default: Default value if key doesn't exist
            
        Returns:
            Deserialized value or default
        """
        try:
            client = await self._get_client()
            raw_value = await client.get(key)
            
            if raw_value is None:
                return default
            
            # Handle different serialization formats based on prefix
            if isinstance(raw_value, bytes):
                # Check for pickle prefix
                if raw_value.startswith(b"pickle:"):
                    return pickle.loads(raw_value[7:])  # Remove "pickle:" prefix
                else:
                    # Convert bytes to string for other formats
                    value = raw_value.decode('utf-8')
            else:
                value = raw_value
            
            # Handle string-based formats
            if isinstance(value, str):
                if value.startswith("json:"):
                    return json.loads(value[5:])  # Remove "json:" prefix
                elif value.startswith("str:"):
                    return value[4:]  # Remove "str:" prefix
                else:
                    # Legacy format - try to deserialize without prefix
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            
            return value
            
        except Exception as e:
            logger.error("Redis get operation failed", key=key, error=str(e))
            return default
    
    async def delete(self, key: str) -> bool:
        """Delete a key from Redis."""
        try:
            client = await self._get_client()
            result = await client.delete(key)
            return result > 0
        except Exception as e:
            logger.error("Redis delete operation failed", key=key, error=str(e))
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if a key exists in Redis."""
        try:
            client = await self._get_client()
            return await client.exists(key)
        except Exception as e:
            logger.error("Redis exists operation failed", key=key, error=str(e))
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration for a key."""
        try:
            client = await self._get_client()
            return await client.expire(key, seconds)
        except Exception as e:
            logger.error("Redis expire operation failed", key=key, error=str(e))
            return False
    
    async def ttl(self, key: str) -> int:
        """Get time to live for a key."""
        try:
            client = await self._get_client()
            return await client.ttl(key)
        except Exception as e:
            logger.error("Redis TTL operation failed", key=key, error=str(e))
            return -1
    
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching a pattern."""
        try:
            client = await self._get_client()
            keys = await client.keys(pattern)
            return [key.decode('utf-8') if isinstance(key, bytes) else key for key in keys]
        except Exception as e:
            logger.error("Redis keys operation failed", pattern=pattern, error=str(e))
            return []
    
    async def flush_pattern(self, pattern: str) -> int:
        """Delete all keys matching a pattern."""
        try:
            keys = await self.keys(pattern)
            if keys:
                client = await self._get_client()
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.error("Redis flush pattern operation failed", pattern=pattern, error=str(e))
            return 0
    
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a numeric value."""
        try:
            client = await self._get_client()
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error("Redis increment operation failed", key=key, error=str(e))
            return 0
    
    async def hash_set(self, key: str, field: str, value: Any) -> bool:
        """Set a hash field."""
        try:
            client = await self._get_client()
            
            # Use consistent serialization
            if isinstance(value, (dict, list)):
                serialized_value = "json:" + json.dumps(value)
            elif isinstance(value, str):
                serialized_value = "str:" + value
            else:
                pickled_data = pickle.dumps(value)
                serialized_value = b"pickle:" + pickled_data
            
            await client.hset(key, field, serialized_value)
            return True
        except Exception as e:
            logger.error("Redis hash set operation failed", key=key, field=field, error=str(e))
            return False
    
    async def hash_get(self, key: str, field: str, default: Any = None) -> Any:
        """Get a hash field."""
        try:
            client = await self._get_client()
            raw_value = await client.hget(key, field)
            
            if raw_value is None:
                return default
            
            # Handle different serialization formats based on prefix
            if isinstance(raw_value, bytes):
                # Check for pickle prefix
                if raw_value.startswith(b"pickle:"):
                    return pickle.loads(raw_value[7:])  # Remove "pickle:" prefix
                else:
                    # Convert bytes to string for other formats
                    value = raw_value.decode('utf-8')
            else:
                value = raw_value
            
            # Handle string-based formats
            if isinstance(value, str):
                if value.startswith("json:"):
                    return json.loads(value[5:])  # Remove "json:" prefix
                elif value.startswith("str:"):
                    return value[4:]  # Remove "str:" prefix
                else:
                    # Legacy format - try to deserialize without prefix
                    try:
                        return json.loads(value)
                    except json.JSONDecodeError:
                        return value
            
            return value
                
        except Exception as e:
            logger.error("Redis hash get operation failed", key=key, field=field, error=str(e))
            return default
    
    async def hash_get_all(self, key: str) -> Dict[str, Any]:
        """Get all hash fields."""
        try:
            client = await self._get_client()
            result = await client.hgetall(key)
            
            # Decode and deserialize all values
            decoded_result = {}
            for field, raw_value in result.items():
                field_str = field.decode('utf-8') if isinstance(field, bytes) else field
                
                # Handle different serialization formats based on prefix
                if isinstance(raw_value, bytes):
                    # Check for pickle prefix
                    if raw_value.startswith(b"pickle:"):
                        decoded_result[field_str] = pickle.loads(raw_value[7:])  # Remove "pickle:" prefix
                    else:
                        # Convert bytes to string for other formats
                        value = raw_value.decode('utf-8')
                else:
                    value = raw_value
                
                # Handle string-based formats
                if isinstance(value, str):
                    if value.startswith("json:"):
                        decoded_result[field_str] = json.loads(value[5:])  # Remove "json:" prefix
                    elif value.startswith("str:"):
                        decoded_result[field_str] = value[4:]  # Remove "str:" prefix
                    else:
                        # Legacy format - try to deserialize without prefix
                        try:
                            decoded_result[field_str] = json.loads(value)
                        except json.JSONDecodeError:
                            decoded_result[field_str] = value
                else:
                    decoded_result[field_str] = value
            
            return decoded_result
            
        except Exception as e:
            logger.error("Redis hash get all operation failed", key=key, error=str(e))
            return {}


# Global service instance
redis_service = RedisService()


class SessionManager:
    """
    Redis-based session manager for user sessions.
    """
    
    def __init__(self, redis_service: RedisService):
        self.redis = redis_service
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.default_ttl = 3600 * 24 * 7  # 7 days
    
    async def create_session(self, user_id: int, session_data: Dict[str, Any], ttl: Optional[int] = None) -> str:
        """
        Create a new user session.
        
        Args:
            user_id: User ID
            session_data: Session data to store
            ttl: Time to live in seconds (default: 7 days)
            
        Returns:
            Session ID
        """
        import uuid
        
        session_id = str(uuid.uuid4())
        session_key = f"{self.session_prefix}{session_id}"
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        
        # Prepare session data
        full_session_data = {
            "user_id": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed": datetime.utcnow().isoformat(),
            **session_data
        }
        
        # Set session data
        await self.redis.set(session_key, full_session_data, ttl or self.default_ttl)
        
        # Track session for user (for multi-session management)
        await self.redis.hash_set(user_sessions_key, session_id, datetime.utcnow().isoformat())
        await self.redis.expire(user_sessions_key, ttl or self.default_ttl)
        
        logger.info("Session created", user_id=user_id, session_id=session_id)
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data by session ID."""
        session_key = f"{self.session_prefix}{session_id}"
        session_data = await self.redis.get(session_key)
        
        if session_data:
            # Update last accessed time
            session_data["last_accessed"] = datetime.utcnow().isoformat()
            await self.redis.set(session_key, session_data, await self.redis.ttl(session_key))
        
        return session_data
    
    async def update_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Update session data."""
        session_key = f"{self.session_prefix}{session_id}"
        
        # Get existing session
        existing_data = await self.redis.get(session_key)
        if not existing_data:
            return False
        
        # Update data
        existing_data.update(session_data)
        existing_data["last_accessed"] = datetime.utcnow().isoformat()
        
        # Save updated data
        ttl = await self.redis.ttl(session_key)
        await self.redis.set(session_key, existing_data, ttl if ttl > 0 else self.default_ttl)
        
        return True
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session_key = f"{self.session_prefix}{session_id}"
        
        # Get session to find user ID
        session_data = await self.redis.get(session_key)
        if session_data and "user_id" in session_data:
            user_sessions_key = f"{self.user_sessions_prefix}{session_data['user_id']}"
            await self.redis.hash_get(user_sessions_key, session_id)  # Remove from user sessions
        
        # Delete session
        result = await self.redis.delete(session_key)
        
        if result:
            logger.info("Session deleted", session_id=session_id)
        
        return result
    
    async def delete_user_sessions(self, user_id: int) -> int:
        """Delete all sessions for a user."""
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        user_sessions = await self.redis.hash_get_all(user_sessions_key)
        
        deleted_count = 0
        for session_id in user_sessions.keys():
            if await self.delete_session(session_id):
                deleted_count += 1
        
        # Delete user sessions tracking
        await self.redis.delete(user_sessions_key)
        
        logger.info("User sessions deleted", user_id=user_id, count=deleted_count)
        return deleted_count
    
    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all sessions for a user."""
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        user_sessions = await self.redis.hash_get_all(user_sessions_key)
        
        sessions = []
        for session_id, created_at in user_sessions.items():
            session_data = await self.get_session(session_id)
            if session_data:
                sessions.append({
                    "session_id": session_id,
                    "created_at": created_at,
                    **session_data
                })
        
        return sessions
    
    async def cleanup_expired_sessions(self):
        """Clean up expired sessions (maintenance task)."""
        logger.info("Starting session cleanup")
        
        # This would typically be run as a background task
        # For now, we rely on Redis TTL for automatic cleanup
        pass


# Global session manager
session_manager = SessionManager(redis_service) 