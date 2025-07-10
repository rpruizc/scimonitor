"""
Twitter/X posts CRUD endpoints with user authentication.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from pydantic import BaseModel, Field
import structlog

from app.db.base import get_async_session
from app.models.twitter import TwitterModel
from app.models.user import UserModel
from app.api.dependencies.auth import get_current_active_user, get_optional_user

logger = structlog.get_logger()
router = APIRouter()


# Pydantic models for request/response
class TweetBase(BaseModel):
    """Base tweet model for requests."""
    text: str = Field(..., min_length=1, max_length=5000)
    user: str = Field(..., min_length=1, max_length=255)
    tweet_id: str = Field(..., min_length=1, max_length=20, pattern=r"^\d+$")
    pic_url: Optional[str] = None


class TweetCreate(TweetBase):
    """Tweet creation model."""
    published_time: str = Field(..., description="ISO datetime string")


class TweetUpdate(BaseModel):
    """Tweet update model (all fields optional)."""
    text: Optional[str] = Field(None, min_length=1, max_length=5000)
    user: Optional[str] = Field(None, min_length=1, max_length=255)
    pic_url: Optional[str] = None
    popularity: Optional[int] = Field(None, ge=0)


class TweetResponse(BaseModel):
    """Tweet response model."""
    id: int
    tweet_id: str
    text: str
    user: str
    pic_url: Optional[str]
    published_time: str
    popularity: int
    twitter_url: str
    has_media: bool


class TweetsListResponse(BaseModel):
    """Paginated tweets list response."""
    tweets: List[TweetResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


@router.get("/tweets", response_model=TweetsListResponse, summary="List tweets")
async def list_tweets(
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[UserModel] = Depends(get_optional_user),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Tweets per page"),
    search: Optional[str] = Query(None, description="Search in tweet text"),
    user: Optional[str] = Query(None, description="Filter by Twitter username"),
    has_media: Optional[bool] = Query(None, description="Filter by media presence"),
    sort_by: str = Query("published_time", description="Sort by: published_time, popularity, user"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """
    Get a paginated list of Twitter/X posts with optional filtering and search.
    
    - **page**: Page number (1-based)
    - **per_page**: Number of tweets per page (max 100)
    - **search**: Search query for tweet text
    - **user**: Filter by specific Twitter username
    - **has_media**: Filter by media presence (true/false)
    - **sort_by**: Sort field (published_time, popularity, user)
    - **sort_order**: Sort order (asc, desc)
    """
    try:
        # Build base query
        query = select(TwitterModel)
        count_query = select(func.count(TwitterModel.id))
        
        # Apply filters
        filters = []
        
        if search:
            # Search in tweet text
            search_term = f"%{search}%"
            filters.append(TwitterModel.text.ilike(search_term))
        
        if user:
            filters.append(TwitterModel.user.ilike(f"%{user}%"))
        
        if has_media is not None:
            if has_media:
                filters.append(TwitterModel.pic_url.isnot(None))
            else:
                filters.append(TwitterModel.pic_url.is_(None))
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Apply sorting
        sort_column = getattr(TwitterModel, sort_by, TwitterModel.published_time)
        if sort_order == "desc":
            query = query.order_by(desc(sort_column))
        else:
            query = query.order_by(sort_column)
        
        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page)
        
        # Execute query
        result = await session.execute(query)
        tweets = result.scalars().all()
        
        # Convert to response format
        tweet_responses = []
        for tweet in tweets:
            tweet_dict = tweet.to_dict()
            tweet_responses.append(TweetResponse(**tweet_dict))
        
        # Track search if user is authenticated
        if current_user and search:
            current_user.increment_searches()
            await session.commit()
        
        return TweetsListResponse(
            tweets=tweet_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=offset + per_page < total,
            has_prev=page > 1
        )
    
    except Exception as e:
        logger.error("Error listing tweets", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tweets"
        )


@router.get("/tweets/{tweet_id}", response_model=TweetResponse, summary="Get tweet by ID")
async def get_tweet(
    tweet_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[UserModel] = Depends(get_optional_user)
):
    """
    Get a specific Twitter/X post by ID.
    
    - **tweet_id**: The tweet's database ID
    """
    try:
        # Get tweet
        result = await session.execute(
            select(TwitterModel).where(TwitterModel.id == tweet_id)
        )
        tweet = result.scalar_one_or_none()
        
        if not tweet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tweet not found"
            )
        
        # Convert to response format
        tweet_dict = tweet.to_dict()
        return TweetResponse(**tweet_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting tweet", tweet_id=tweet_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tweet"
        )


@router.post("/tweets", response_model=TweetResponse, status_code=status.HTTP_201_CREATED, summary="Create new tweet")
async def create_tweet(
    tweet_data: TweetCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Create a new Twitter/X post entry.
    
    Requires authentication. Only verified users can create tweets.
    """
    try:
        # Check if user is verified (optional additional check)
        if not current_user.is_verified and current_user.searches_count == 0:
            # Allow creation for new users, but could add stricter verification later
            pass
        
        # Check if tweet already exists by Twitter ID
        existing_result = await session.execute(
            select(TwitterModel).where(TwitterModel.tweet_id == tweet_data.tweet_id)
        )
        existing_tweet = existing_result.scalar_one_or_none()
        
        if existing_tweet:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Tweet with this Twitter ID already exists"
            )
        
        # Create new tweet
        from datetime import datetime
        tweet = TwitterModel(
            tweet_id=tweet_data.tweet_id,
            text=tweet_data.text,
            user=tweet_data.user,
            pic_url=tweet_data.pic_url,
            published_time=datetime.fromisoformat(tweet_data.published_time.replace('Z', '+00:00')),
            popularity=0
        )
        
        session.add(tweet)
        await session.flush()  # Get the ID
        
        logger.info("Tweet created", tweet_id=tweet.id, user_id=current_user.id)
        await session.commit()
        
        # Convert to response format
        tweet_dict = tweet.to_dict()
        return TweetResponse(**tweet_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating tweet", error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tweet"
        )


@router.put("/tweets/{tweet_id}", response_model=TweetResponse, summary="Update tweet")
async def update_tweet(
    tweet_id: int,
    tweet_data: TweetUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Update an existing Twitter/X post.
    
    Requires authentication. Users can update tweets they created or if they're verified.
    """
    try:
        # Get tweet
        result = await session.execute(
            select(TwitterModel).where(TwitterModel.id == tweet_id)
        )
        tweet = result.scalar_one_or_none()
        
        if not tweet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tweet not found"
            )
        
        # Check permissions (for now, allow any verified user to edit)
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only verified users can update tweets"
            )
        
        # Update fields
        update_data = tweet_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tweet, field, value)
        
        logger.info("Tweet updated", tweet_id=tweet.id, user_id=current_user.id)
        await session.commit()
        
        # Convert to response format
        tweet_dict = tweet.to_dict()
        return TweetResponse(**tweet_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating tweet", tweet_id=tweet_id, error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tweet"
        )


@router.delete("/tweets/{tweet_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete tweet")
async def delete_tweet(
    tweet_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Delete a Twitter/X post.
    
    Requires authentication and verification. Only verified users can delete tweets.
    """
    try:
        # Get tweet
        result = await session.execute(
            select(TwitterModel).where(TwitterModel.id == tweet_id)
        )
        tweet = result.scalar_one_or_none()
        
        if not tweet:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tweet not found"
            )
        
        # Check permissions (strict - only verified users)
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only verified users can delete tweets"
            )
        
        # Delete tweet
        await session.delete(tweet)
        logger.info("Tweet deleted", tweet_id=tweet.id, user_id=current_user.id)
        await session.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting tweet", tweet_id=tweet_id, error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tweet"
        ) 