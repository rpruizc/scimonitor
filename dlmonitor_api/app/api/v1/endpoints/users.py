"""
User-specific endpoints for profile, preferences, and saved papers.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel, Field
import structlog

from app.db.base import get_async_session
from app.models.user import UserModel
from app.models.arxiv import ArxivModel
from app.api.dependencies.auth import get_current_active_user
from app.api.v1.endpoints.papers import PaperResponse

logger = structlog.get_logger()
router = APIRouter()


# Pydantic models for user operations
class UserProfile(BaseModel):
    """User profile response."""
    id: int
    email: str
    display_name: str
    avatar_url: Optional[str]
    github_username: Optional[str]
    research_interests: Optional[str]
    affiliation: Optional[str]
    orcid_id: Optional[str]
    is_verified: bool
    created_at: str
    papers_saved_count: int
    searches_count: int


class UserProfileUpdate(BaseModel):
    """User profile update model."""
    full_name: Optional[str] = Field(None, max_length=255)
    research_interests: Optional[str] = None
    affiliation: Optional[str] = Field(None, max_length=255)
    orcid_id: Optional[str] = Field(None, max_length=25, pattern=r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$")


class UserPreferences(BaseModel):
    """User preferences model."""
    email_notifications: bool = True
    paper_alerts: bool = True
    tweet_alerts: bool = False
    search_history_enabled: bool = True
    public_profile: bool = False
    preferred_fields: List[str] = []
    notification_frequency: str = "daily"  # daily, weekly, monthly, never


class SavedPaperCreate(BaseModel):
    """Model for saving a paper."""
    paper_id: int
    notes: Optional[str] = None
    tags: List[str] = []


class SavedPaper(BaseModel):
    """Saved paper response model."""
    paper: PaperResponse
    saved_at: str
    notes: Optional[str]
    tags: List[str]


@router.get("/users/me", response_model=UserProfile, summary="Get current user profile")
async def get_current_user_profile(
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get the current user's profile information.
    """
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        display_name=current_user.display_name,
        avatar_url=current_user.profile_image,
        github_username=current_user.github_username,
        research_interests=current_user.research_interests,
        affiliation=current_user.affiliation,
        orcid_id=current_user.orcid_id,
        is_verified=current_user.is_verified,
        created_at=current_user.created_at.isoformat(),
        papers_saved_count=current_user.papers_saved_count,
        searches_count=current_user.searches_count,
    )


@router.put("/users/me", response_model=UserProfile, summary="Update current user profile")
async def update_current_user_profile(
    profile_data: UserProfileUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Update the current user's profile information.
    """
    try:
        # Update fields
        update_data = profile_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        logger.info("User profile updated", user_id=current_user.id)
        await session.commit()
        
        return UserProfile(
            id=current_user.id,
            email=current_user.email,
            display_name=current_user.display_name,
            avatar_url=current_user.profile_image,
            github_username=current_user.github_username,
            research_interests=current_user.research_interests,
            affiliation=current_user.affiliation,
            orcid_id=current_user.orcid_id,
            is_verified=current_user.is_verified,
            created_at=current_user.created_at.isoformat(),
            papers_saved_count=current_user.papers_saved_count,
            searches_count=current_user.searches_count,
        )
    
    except Exception as e:
        logger.error("Error updating user profile", error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/users/me/preferences", response_model=UserPreferences, summary="Get user preferences")
async def get_user_preferences(
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Get the current user's preferences.
    """
    # Return preferences with defaults
    prefs = current_user.preferences or {}
    return UserPreferences(
        email_notifications=prefs.get("email_notifications", True),
        paper_alerts=prefs.get("paper_alerts", True),
        tweet_alerts=prefs.get("tweet_alerts", False),
        search_history_enabled=prefs.get("search_history_enabled", True),
        public_profile=prefs.get("public_profile", False),
        preferred_fields=prefs.get("preferred_fields", []),
        notification_frequency=prefs.get("notification_frequency", "daily"),
    )


@router.put("/users/me/preferences", response_model=UserPreferences, summary="Update user preferences")
async def update_user_preferences(
    preferences: UserPreferences,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Update the current user's preferences.
    """
    try:
        # Update preferences
        current_user.update_preferences(preferences.dict())
        
        logger.info("User preferences updated", user_id=current_user.id)
        await session.commit()
        
        return preferences
    
    except Exception as e:
        logger.error("Error updating user preferences", error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update preferences"
        )


@router.post("/users/me/saved-papers", status_code=status.HTTP_201_CREATED, summary="Save a paper")
async def save_paper(
    save_data: SavedPaperCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Save a paper to the user's collection.
    """
    try:
        # Check if paper exists
        paper_result = await session.execute(
            select(ArxivModel).where(ArxivModel.id == save_data.paper_id)
        )
        paper = paper_result.scalar_one_or_none()
        
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found"
            )
        
        # For now, store saved papers in user preferences
        # In a full implementation, you'd want a separate SavedPaper model
        saved_papers = current_user.get_preference("saved_papers", [])
        
        # Check if already saved
        paper_ids = [sp.get("paper_id") for sp in saved_papers]
        if save_data.paper_id in paper_ids:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Paper already saved"
            )
        
        # Add to saved papers
        from datetime import datetime
        saved_paper_data = {
            "paper_id": save_data.paper_id,
            "saved_at": datetime.utcnow().isoformat(),
            "notes": save_data.notes,
            "tags": save_data.tags
        }
        saved_papers.append(saved_paper_data)
        
        # Update user preferences and count
        current_user.update_preferences({"saved_papers": saved_papers})
        current_user.increment_papers_saved()
        
        logger.info("Paper saved", paper_id=save_data.paper_id, user_id=current_user.id)
        await session.commit()
        
        return {"message": "Paper saved successfully", "paper_id": save_data.paper_id}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error saving paper", error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save paper"
        )


@router.get("/users/me/saved-papers", response_model=List[SavedPaper], summary="Get saved papers")
async def get_saved_papers(
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Papers per page")
):
    """
    Get the current user's saved papers.
    """
    try:
        saved_papers = current_user.get_preference("saved_papers", [])
        
        if not saved_papers:
            return []
        
        # Get paper IDs
        paper_ids = [sp["paper_id"] for sp in saved_papers]
        
        # Fetch papers from database
        papers_result = await session.execute(
            select(ArxivModel).where(ArxivModel.id.in_(paper_ids))
        )
        papers = papers_result.scalars().all()
        papers_dict = {paper.id: paper for paper in papers}
        
        # Build response
        saved_paper_responses = []
        for saved_paper_data in saved_papers:
            paper_id = saved_paper_data["paper_id"]
            if paper_id in papers_dict:
                paper = papers_dict[paper_id]
                saved_paper_responses.append(SavedPaper(
                    paper=PaperResponse(**paper.to_dict()),
                    saved_at=saved_paper_data["saved_at"],
                    notes=saved_paper_data.get("notes"),
                    tags=saved_paper_data.get("tags", [])
                ))
        
        # Apply pagination (simple in-memory pagination for now)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = saved_paper_responses[start_idx:end_idx]
        
        return paginated_results
    
    except Exception as e:
        logger.error("Error getting saved papers", error=str(e), user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get saved papers"
        )


@router.delete("/users/me/saved-papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove saved paper")
async def remove_saved_paper(
    paper_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Remove a paper from the user's saved collection.
    """
    try:
        saved_papers = current_user.get_preference("saved_papers", [])
        
        # Find and remove the paper
        updated_saved_papers = [sp for sp in saved_papers if sp.get("paper_id") != paper_id]
        
        if len(updated_saved_papers) == len(saved_papers):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Saved paper not found"
            )
        
        # Update preferences
        current_user.update_preferences({"saved_papers": updated_saved_papers})
        
        logger.info("Saved paper removed", paper_id=paper_id, user_id=current_user.id)
        await session.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error removing saved paper", error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove saved paper"
        )


@router.get("/users/{user_id}/public", response_model=UserProfile, summary="Get public user profile")
async def get_public_user_profile(
    user_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get a user's public profile information.
    Only returns public information if the user has enabled public profile.
    """
    try:
        # Get user
        result = await session.execute(
            select(UserModel).where(UserModel.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check if profile is public
        if not user.get_preference("public_profile", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User profile is private"
            )
        
        # Return limited public information
        return user.to_public_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting public user profile", error=str(e), user_id=user_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        ) 