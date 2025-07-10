"""
Supabase authentication configuration and utilities.
"""

from typing import Optional, Dict, Any
from supabase import create_client, Client
from gotrue.errors import AuthError
import structlog

from app.core.settings import settings

logger = structlog.get_logger()

# Supabase client instance
supabase_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client instance.
    """
    global supabase_client
    
    if supabase_client is None:
        if not settings.supabase_url or not settings.supabase_anon_key:
            logger.warning("Supabase credentials not configured")
            raise ValueError("Supabase URL and anon key must be configured")
        
        supabase_client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )
        logger.info("Supabase client initialized")
    
    return supabase_client


async def verify_supabase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a Supabase JWT token and return user data.
    
    Args:
        token: JWT token from Supabase Auth
        
    Returns:
        User data dict if valid, None if invalid
    """
    try:
        client = get_supabase_client()
        
        # Set the session with the provided token
        auth_response = client.auth.set_session(access_token=token, refresh_token="")
        
        if auth_response.user:
            user_data = {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "email_confirmed": auth_response.user.email_confirmed_at is not None,
                "created_at": auth_response.user.created_at,
                "last_sign_in": auth_response.user.last_sign_in_at,
                "app_metadata": auth_response.user.app_metadata or {},
                "user_metadata": auth_response.user.user_metadata or {},
            }
            
            # Extract provider info (GitHub, Google, etc.)
            identities = auth_response.user.identities or []
            if identities:
                provider_data = identities[0]
                user_data["provider"] = provider_data.provider
                user_data["provider_id"] = provider_data.id
                user_data["provider_data"] = provider_data.identity_data or {}
            
            return user_data
        
        return None
        
    except AuthError as e:
        logger.warning("Supabase token verification failed", error=str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error verifying Supabase token", error=str(e))
        return None


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Get user data by Supabase user ID.
    
    Args:
        user_id: Supabase user ID
        
    Returns:
        User data dict if found, None if not found
    """
    try:
        client = get_supabase_client()
        
        # Note: This requires service key for admin operations
        if not settings.supabase_service_key:
            logger.warning("Service key not configured for admin operations")
            return None
        
        # Use admin client for user lookup
        admin_client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
        
        response = admin_client.auth.admin.get_user_by_id(user_id)
        if response.user:
            return {
                "id": response.user.id,
                "email": response.user.email,
                "email_confirmed": response.user.email_confirmed_at is not None,
                "created_at": response.user.created_at,
                "last_sign_in": response.user.last_sign_in_at,
                "app_metadata": response.user.app_metadata or {},
                "user_metadata": response.user.user_metadata or {},
            }
        
        return None
        
    except Exception as e:
        logger.error("Error getting user by ID", user_id=user_id, error=str(e))
        return None


def extract_github_info(user_data: Dict[str, Any]) -> Dict[str, Optional[str]]:
    """
    Extract GitHub-specific information from Supabase user data.
    
    Args:
        user_data: User data from Supabase
        
    Returns:
        Dict with GitHub username, avatar, etc.
    """
    github_info = {
        "github_username": None,
        "github_avatar": None,
        "github_name": None,
    }
    
    if user_data.get("provider") == "github":
        provider_data = user_data.get("provider_data", {})
        github_info.update({
            "github_username": provider_data.get("user_name"),
            "github_avatar": provider_data.get("avatar_url"),
            "github_name": provider_data.get("full_name"),
        })
    
    return github_info 