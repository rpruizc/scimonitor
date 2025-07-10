"""
Unified search functionality across papers and tweets.
"""

from typing import Optional, List, Union
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc, text
from pydantic import BaseModel, Field
import structlog

from app.db.base import get_async_session
from app.models.arxiv import ArxivModel
from app.models.twitter import TwitterModel
from app.models.user import UserModel
from app.api.dependencies.auth import get_optional_user
from app.api.v1.endpoints.papers import PaperResponse
from app.api.v1.endpoints.tweets import TweetResponse

logger = structlog.get_logger()
router = APIRouter()


# Pydantic models for search responses
class SearchResultItem(BaseModel):
    """Individual search result item."""
    type: str  # "paper" or "tweet"
    relevance_score: float
    data: Union[PaperResponse, TweetResponse]


class SearchResponse(BaseModel):
    """Unified search response."""
    results: List[SearchResultItem]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
    query: str
    search_time_ms: float


class SearchStats(BaseModel):
    """Search statistics response."""
    papers_count: int
    tweets_count: int
    total_count: int
    papers_analyzed: int
    tweets_with_media: int


@router.get("/search", response_model=SearchResponse, summary="Unified search")
async def unified_search(
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[UserModel] = Depends(get_optional_user),
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Results per page"),
    content_type: str = Query("all", description="Content type: all, papers, tweets"),
    sort_by: str = Query("relevance", description="Sort by: relevance, date, popularity"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)")
):
    """
    Unified search across ArXiv papers and Twitter posts.
    
    - **q**: Search query (required)
    - **page**: Page number (1-based)
    - **per_page**: Number of results per page (max 100)
    - **content_type**: Filter by content type (all, papers, tweets)
    - **sort_by**: Sort by relevance, date, or popularity
    - **sort_order**: Sort order (asc, desc)
    - **date_from**: Filter results from this date
    - **date_to**: Filter results to this date
    """
    import time
    start_time = time.time()
    
    try:
        results = []
        
        # Search in papers if requested
        if content_type in ["all", "papers"]:
            paper_results = await _search_papers(session, q, date_from, date_to)
            for paper in paper_results:
                score = _calculate_relevance_score(q, paper.title, paper.abstract, paper.authors)
                results.append(SearchResultItem(
                    type="paper",
                    relevance_score=score,
                    data=PaperResponse(**paper.to_dict())
                ))
        
        # Search in tweets if requested
        if content_type in ["all", "tweets"]:
            tweet_results = await _search_tweets(session, q, date_from, date_to)
            for tweet in tweet_results:
                score = _calculate_relevance_score(q, tweet.text, tweet.user, "")
                results.append(SearchResultItem(
                    type="tweet",
                    relevance_score=score,
                    data=TweetResponse(**tweet.to_dict())
                ))
        
        # Sort results
        if sort_by == "relevance":
            results.sort(key=lambda x: x.relevance_score, reverse=(sort_order == "desc"))
        elif sort_by == "date":
            results.sort(
                key=lambda x: x.data.published_time, 
                reverse=(sort_order == "desc")
            )
        elif sort_by == "popularity":
            results.sort(
                key=lambda x: x.data.popularity, 
                reverse=(sort_order == "desc")
            )
        
        # Apply pagination
        total = len(results)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_results = results[start_idx:end_idx]
        
        # Track search if user is authenticated
        if current_user:
            current_user.increment_searches()
            await session.commit()
        
        search_time_ms = (time.time() - start_time) * 1000
        
        return SearchResponse(
            results=paginated_results,
            total=total,
            page=page,
            per_page=per_page,
            has_next=end_idx < total,
            has_prev=page > 1,
            query=q,
            search_time_ms=search_time_ms
        )
    
    except Exception as e:
        logger.error("Error in unified search", error=str(e), query=q)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed"
        )


@router.get("/search/papers", response_model=List[PaperResponse], summary="Search papers only")
async def search_papers_only(
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[UserModel] = Depends(get_optional_user),
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results")
):
    """
    Search specifically in ArXiv papers.
    
    - **q**: Search query (required)
    - **limit**: Maximum number of results (max 100)
    """
    try:
        paper_results = await _search_papers(session, q, None, None, limit)
        
        # Track search if user is authenticated
        if current_user:
            current_user.increment_searches()
            await session.commit()
        
        return [PaperResponse(**paper.to_dict()) for paper in paper_results]
    
    except Exception as e:
        logger.error("Error searching papers", error=str(e), query=q)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Paper search failed"
        )


@router.get("/search/tweets", response_model=List[TweetResponse], summary="Search tweets only")
async def search_tweets_only(
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[UserModel] = Depends(get_optional_user),
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results")
):
    """
    Search specifically in Twitter posts.
    
    - **q**: Search query (required)
    - **limit**: Maximum number of results (max 100)
    """
    try:
        tweet_results = await _search_tweets(session, q, None, None, limit)
        
        # Track search if user is authenticated
        if current_user:
            current_user.increment_searches()
            await session.commit()
        
        return [TweetResponse(**tweet.to_dict()) for tweet in tweet_results]
    
    except Exception as e:
        logger.error("Error searching tweets", error=str(e), query=q)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Tweet search failed"
        )


@router.get("/search/stats", response_model=SearchStats, summary="Search statistics")
async def search_statistics(
    session: AsyncSession = Depends(get_async_session)
):
    """
    Get search and content statistics.
    """
    try:
        # Get papers count
        papers_count_result = await session.execute(select(func.count(ArxivModel.id)))
        papers_count = papers_count_result.scalar()
        
        # Get analyzed papers count
        analyzed_papers_result = await session.execute(
            select(func.count(ArxivModel.id)).where(ArxivModel.analyzed == True)
        )
        papers_analyzed = analyzed_papers_result.scalar()
        
        # Get tweets count
        tweets_count_result = await session.execute(select(func.count(TwitterModel.id)))
        tweets_count = tweets_count_result.scalar()
        
        # Get tweets with media count
        tweets_media_result = await session.execute(
            select(func.count(TwitterModel.id)).where(TwitterModel.pic_url.isnot(None))
        )
        tweets_with_media = tweets_media_result.scalar()
        
        return SearchStats(
            papers_count=papers_count,
            tweets_count=tweets_count,
            total_count=papers_count + tweets_count,
            papers_analyzed=papers_analyzed,
            tweets_with_media=tweets_with_media
        )
    
    except Exception as e:
        logger.error("Error getting search stats", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


async def _search_papers(
    session: AsyncSession, 
    query: str, 
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
) -> List[ArxivModel]:
    """Search in ArXiv papers."""
    search_term = f"%{query}%"
    
    # Build query with PostgreSQL full-text search if available
    db_query = select(ArxivModel).where(
        or_(
            ArxivModel.title.ilike(search_term),
            ArxivModel.abstract.ilike(search_term),
            ArxivModel.authors.ilike(search_term)
        )
    )
    
    # Add date filters
    if date_from:
        from datetime import datetime
        date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        db_query = db_query.where(ArxivModel.published_time >= date_from_dt)
    
    if date_to:
        from datetime import datetime
        date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        db_query = db_query.where(ArxivModel.published_time <= date_to_dt)
    
    # Order by relevance (popularity for now, could be enhanced)
    db_query = db_query.order_by(desc(ArxivModel.popularity), desc(ArxivModel.published_time))
    db_query = db_query.limit(limit)
    
    result = await session.execute(db_query)
    return result.scalars().all()


async def _search_tweets(
    session: AsyncSession, 
    query: str, 
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 100
) -> List[TwitterModel]:
    """Search in Twitter posts."""
    search_term = f"%{query}%"
    
    db_query = select(TwitterModel).where(
        or_(
            TwitterModel.text.ilike(search_term),
            TwitterModel.user.ilike(search_term)
        )
    )
    
    # Add date filters
    if date_from:
        from datetime import datetime
        date_from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        db_query = db_query.where(TwitterModel.published_time >= date_from_dt)
    
    if date_to:
        from datetime import datetime
        date_to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
        db_query = db_query.where(TwitterModel.published_time <= date_to_dt)
    
    # Order by relevance (popularity for now)
    db_query = db_query.order_by(desc(TwitterModel.popularity), desc(TwitterModel.published_time))
    db_query = db_query.limit(limit)
    
    result = await session.execute(db_query)
    return result.scalars().all()


def _calculate_relevance_score(query: str, title: str, content: str, author: str) -> float:
    """
    Calculate relevance score for search results.
    Simple implementation - can be enhanced with more sophisticated algorithms.
    """
    query_lower = query.lower()
    title_lower = title.lower()
    content_lower = content.lower()
    author_lower = author.lower()
    
    score = 0.0
    
    # Exact phrase matches get higher scores
    if query_lower in title_lower:
        score += 5.0
    if query_lower in content_lower:
        score += 3.0
    if query_lower in author_lower:
        score += 2.0
    
    # Individual word matches
    query_words = query_lower.split()
    for word in query_words:
        if len(word) > 2:  # Skip very short words
            if word in title_lower:
                score += 2.0
            if word in content_lower:
                score += 1.0
            if word in author_lower:
                score += 1.5
    
    return score 