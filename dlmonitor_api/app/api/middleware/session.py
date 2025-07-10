"""
Session management middleware for handling user sessions with Redis.
"""

from typing import Optional, Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import uuid
import structlog

from app.core.redis import session_manager
from app.core.settings import settings

logger = structlog.get_logger()


class SessionMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle user sessions with Redis backend.
    
    This middleware:
    - Creates sessions for authenticated users
    - Manages session cookies
    - Provides session data to endpoints
    - Handles session cleanup
    """
    
    def __init__(
        self,
        app: ASGIApp,
        session_cookie_name: str = "session_id",
        session_cookie_max_age: int = 7 * 24 * 3600,  # 7 days
        session_cookie_secure: bool = True,
        session_cookie_httponly: bool = True,
        session_cookie_samesite: str = "lax"
    ):
        super().__init__(app)
        self.session_cookie_name = session_cookie_name
        self.session_cookie_max_age = session_cookie_max_age
        self.session_cookie_secure = session_cookie_secure and settings.is_production
        self.session_cookie_httponly = session_cookie_httponly
        self.session_cookie_samesite = session_cookie_samesite
    
    async def dispatch(self, request: Request, call_next):
        """
        Process the request and manage session.
        """
        # Get existing session ID from cookie
        session_id = request.cookies.get(self.session_cookie_name)
        session_data = None
        
        if session_id:
            try:
                # Try to load existing session
                session_data = await session_manager.get_session(session_id)
                if session_data:
                    # Add session data to request state
                    request.state.session_id = session_id
                    request.state.session_data = session_data
                    request.state.session_user_id = session_data.get("user_id")
                else:
                    # Session doesn't exist or expired
                    session_id = None
            except Exception as e:
                logger.warning("Failed to load session", session_id=session_id, error=str(e))
                session_id = None
        
        # If no valid session, initialize empty session state
        if not session_id:
            request.state.session_id = None
            request.state.session_data = {}
            request.state.session_user_id = None
        
        # Process the request
        response = await call_next(request)
        
        # Handle session management after request processing
        await self._handle_session_response(request, response)
        
        return response
    
    async def _handle_session_response(self, request: Request, response: Response):
        """
        Handle session creation/updates after request processing.
        """
        try:
            # Check if a new session was created during request processing
            if hasattr(request.state, 'create_session') and request.state.create_session:
                user_id = request.state.session_user_id
                session_data = getattr(request.state, 'new_session_data', {})
                
                if user_id:
                    # Create new session
                    session_id = await session_manager.create_session(
                        user_id=user_id,
                        session_data=session_data,
                        ttl=self.session_cookie_max_age
                    )
                    
                    # Set session cookie
                    response.set_cookie(
                        key=self.session_cookie_name,
                        value=session_id,
                        max_age=self.session_cookie_max_age,
                        secure=self.session_cookie_secure,
                        httponly=self.session_cookie_httponly,
                        samesite=self.session_cookie_samesite
                    )
                    
                    logger.info("Session created", session_id=session_id, user_id=user_id)
            
            # Check if session data was updated
            elif hasattr(request.state, 'update_session') and request.state.update_session:
                session_id = request.state.session_id
                session_data = getattr(request.state, 'updated_session_data', {})
                
                if session_id and session_data:
                    await session_manager.update_session(session_id, session_data)
                    logger.debug("Session updated", session_id=session_id)
            
            # Check if session should be destroyed
            elif hasattr(request.state, 'destroy_session') and request.state.destroy_session:
                session_id = request.state.session_id
                
                if session_id:
                    await session_manager.delete_session(session_id)
                    
                    # Clear session cookie
                    response.delete_cookie(
                        key=self.session_cookie_name,
                        secure=self.session_cookie_secure,
                        httponly=self.session_cookie_httponly,
                        samesite=self.session_cookie_samesite
                    )
                    
                    logger.info("Session destroyed", session_id=session_id)
        
        except Exception as e:
            logger.error("Error handling session response", error=str(e))


# Session helper functions that can be used in endpoints
async def create_user_session(
    request: Request,
    user_id: int,
    session_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Mark a session for creation after request processing.
    
    Args:
        request: FastAPI request object
        user_id: User ID to create session for
        session_data: Additional session data to store
    """
    request.state.create_session = True
    request.state.session_user_id = user_id
    request.state.new_session_data = session_data or {}


async def update_user_session(
    request: Request,
    session_data: Dict[str, Any]
) -> None:
    """
    Mark session data for update after request processing.
    
    Args:
        request: FastAPI request object
        session_data: Session data to update
    """
    request.state.update_session = True
    request.state.updated_session_data = session_data


async def destroy_user_session(request: Request) -> None:
    """
    Mark session for destruction after request processing.
    
    Args:
        request: FastAPI request object
    """
    request.state.destroy_session = True


def get_session_data(request: Request) -> Dict[str, Any]:
    """
    Get current session data from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Session data dictionary
    """
    return getattr(request.state, 'session_data', {})


def get_session_user_id(request: Request) -> Optional[int]:
    """
    Get current session user ID from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User ID if session exists, None otherwise
    """
    return getattr(request.state, 'session_user_id', None)


def get_session_id(request: Request) -> Optional[str]:
    """
    Get current session ID from request.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Session ID if session exists, None otherwise
    """
    return getattr(request.state, 'session_id', None)


def has_session(request: Request) -> bool:
    """
    Check if request has a valid session.
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if session exists, False otherwise
    """
    return bool(getattr(request.state, 'session_id', None)) 