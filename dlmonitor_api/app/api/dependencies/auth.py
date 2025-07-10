"""
Authentication dependencies for FastAPI endpoints.
Integrates with Supabase Auth for JWT token verification.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import structlog

from app.core.auth import verify_supabase_token, extract_github_info
from app.db.base import get_async_session
from app.models.user import UserModel

logger = structlog.get_logger()

# HTTP Bearer token scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    session: AsyncSession = Depends(get_async_session),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserModel:
    """
    Get the current authenticated user from Supabase JWT token.
    
    Args:
        session: Database session
        credentials: HTTP Bearer credentials from request
        
    Returns:
        UserModel instance
        
    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    # Verify token with Supabase
    supabase_user = await verify_supabase_token(credentials.credentials)
    if not supabase_user:
        raise credentials_exception
    
    # Get or create user in our database
    user = await get_or_create_user(session, supabase_user)
    if not user:
        logger.error("Failed to get/create user", supabase_id=supabase_user.get("id"))
        raise credentials_exception
    
    # Update last login
    user.update_last_login()
    await session.commit()
    
    return user


async def get_current_active_user(
    current_user: UserModel = Depends(get_current_user)
) -> UserModel:
    """
    Get the current authenticated and active user.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        UserModel instance if active
        
    Raises:
        HTTPException: If user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return current_user


async def get_optional_user(
    session: AsyncSession = Depends(get_async_session),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[UserModel]:
    """
    Get the current user if authenticated, None otherwise.
    Useful for endpoints that work with or without authentication.
    
    Args:
        session: Database session
        credentials: HTTP Bearer credentials from request
        
    Returns:
        UserModel instance if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        # Verify token with Supabase
        supabase_user = await verify_supabase_token(credentials.credentials)
        if not supabase_user:
            return None
        
        # Get or create user in our database
        user = await get_or_create_user(session, supabase_user)
        if user:
            user.update_last_login()
            await session.commit()
        
        return user
        
    except Exception as e:
        logger.warning("Optional auth failed", error=str(e))
        return None


async def get_or_create_user(
    session: AsyncSession, 
    supabase_user: dict
) -> Optional[UserModel]:
    """
    Get existing user or create new user from Supabase data.
    
    Args:
        session: Database session
        supabase_user: User data from Supabase
        
    Returns:
        UserModel instance or None if creation fails
    """
    try:
        supabase_id = supabase_user["id"]
        email = supabase_user["email"]
        
        # Try to find existing user
        result = await session.execute(
            select(UserModel).where(UserModel.supabase_id == supabase_id)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # Update existing user with latest Supabase data
            await update_user_from_supabase(user, supabase_user)
            return user
        
        # Create new user
        github_info = extract_github_info(supabase_user)
        
        user = UserModel(
            supabase_id=supabase_id,
            email=email,
            email_confirmed=supabase_user.get("email_confirmed", False),
            full_name=supabase_user.get("user_metadata", {}).get("full_name"),
            avatar_url=supabase_user.get("user_metadata", {}).get("avatar_url"),
            auth_provider=supabase_user.get("provider"),
            github_username=github_info.get("github_username"),
            github_avatar=github_info.get("github_avatar"),
            preferences={}
        )
        
        session.add(user)
        await session.flush()  # Get the ID without committing
        
        logger.info("Created new user", user_id=user.id, supabase_id=supabase_id)
        return user
        
    except Exception as e:
        logger.error("Error getting/creating user", error=str(e), supabase_id=supabase_user.get("id"))
        await session.rollback()
        return None


async def update_user_from_supabase(user: UserModel, supabase_user: dict) -> None:
    """
    Update user model with latest data from Supabase.
    
    Args:
        user: Existing user model
        supabase_user: Latest data from Supabase
    """
    # Update basic fields
    user.email = supabase_user["email"]
    user.email_confirmed = supabase_user.get("email_confirmed", False)
    
    # Update metadata if available
    user_metadata = supabase_user.get("user_metadata", {})
    if user_metadata.get("full_name"):
        user.full_name = user_metadata["full_name"]
    if user_metadata.get("avatar_url"):
        user.avatar_url = user_metadata["avatar_url"]
    
    # Update GitHub info if provider is GitHub
    github_info = extract_github_info(supabase_user)
    if github_info["github_username"]:
        user.github_username = github_info["github_username"]
        user.github_avatar = github_info["github_avatar"]
        user.auth_provider = "github" 