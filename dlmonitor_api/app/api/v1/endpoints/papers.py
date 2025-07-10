"""
ArXiv papers CRUD endpoints with user authentication.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
import structlog

from app.db.base import get_async_session
from app.models.arxiv import ArxivModel
from app.models.user import UserModel
from app.api.dependencies.auth import get_current_active_user, get_optional_user

logger = structlog.get_logger()
router = APIRouter()


# Pydantic models for request/response
class PaperBase(BaseModel):
    """Base paper model for requests."""
    title: str = Field(..., min_length=1, max_length=800)
    authors: str = Field(..., min_length=1, max_length=800)
    abstract: str = Field(..., min_length=1)
    arxiv_url: str = Field(..., pattern=r"^https?://arxiv\.org/abs/[\w.-]+$")
    pdf_url: str = Field(..., pattern=r"^https?://.*\.pdf$")
    journal_link: Optional[str] = None
    tag: Optional[str] = None


class PaperCreate(PaperBase):
    """Paper creation model."""
    published_time: str = Field(..., description="ISO datetime string")


class PaperUpdate(BaseModel):
    """Paper update model (all fields optional)."""
    title: Optional[str] = Field(None, min_length=1, max_length=800)
    authors: Optional[str] = Field(None, min_length=1, max_length=800)
    abstract: Optional[str] = None
    journal_link: Optional[str] = None
    tag: Optional[str] = None
    introduction: Optional[str] = None
    conclusion: Optional[str] = None
    analyzed: Optional[bool] = None


class PaperResponse(BaseModel):
    """Paper response model."""
    id: int
    arxiv_id: str
    arxiv_url: str
    pdf_url: str
    title: str
    authors: List[str]
    abstract: str
    published_time: str
    journal_link: Optional[str]
    tags: List[str]
    popularity: int
    analyzed: bool
    introduction: Optional[str]
    conclusion: Optional[str]
    version: Optional[int]


class PapersListResponse(BaseModel):
    """Paginated papers list response."""
    papers: List[PaperResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


@router.get("/papers", response_model=PapersListResponse, summary="List papers")
async def list_papers(
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[UserModel] = Depends(get_optional_user),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Papers per page"),
    search: Optional[str] = Query(None, description="Search in title, authors, abstract"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    analyzed: Optional[bool] = Query(None, description="Filter by analysis status"),
    sort_by: str = Query("published_time", description="Sort by: published_time, popularity, title"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order")
):
    """
    Get a paginated list of ArXiv papers with optional filtering and search.
    
    - **page**: Page number (1-based)
    - **per_page**: Number of papers per page (max 100)
    - **search**: Search query for title, authors, or abstract
    - **tag**: Filter by specific tag
    - **analyzed**: Filter by analysis status
    - **sort_by**: Sort field (published_time, popularity, title)
    - **sort_order**: Sort order (asc, desc)
    """
    try:
        # Build base query
        query = select(ArxivModel)
        count_query = select(func.count(ArxivModel.id))
        
        # Apply filters
        filters = []
        
        if search:
            # Search in title, authors, or abstract
            search_term = f"%{search}%"
            filters.append(
                or_(
                    ArxivModel.title.ilike(search_term),
                    ArxivModel.authors.ilike(search_term),
                    ArxivModel.abstract.ilike(search_term)
                )
            )
        
        if tag:
            filters.append(ArxivModel.tag.ilike(f"%{tag}%"))
        
        if analyzed is not None:
            filters.append(ArxivModel.analyzed == analyzed)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Apply sorting
        sort_column = getattr(ArxivModel, sort_by, ArxivModel.published_time)
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
        papers = result.scalars().all()
        
        # Convert to response format
        paper_responses = []
        for paper in papers:
            paper_dict = paper.to_dict()
            paper_responses.append(PaperResponse(**paper_dict))
        
        # Track search if user is authenticated
        if current_user and search:
            current_user.increment_searches()
            await session.commit()
        
        return PapersListResponse(
            papers=paper_responses,
            total=total,
            page=page,
            per_page=per_page,
            has_next=offset + per_page < total,
            has_prev=page > 1
        )
    
    except Exception as e:
        logger.error("Error listing papers", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve papers"
        )


@router.get("/papers/{paper_id}", response_model=PaperResponse, summary="Get paper by ID")
async def get_paper(
    paper_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: Optional[UserModel] = Depends(get_optional_user)
):
    """
    Get a specific ArXiv paper by ID.
    
    - **paper_id**: The paper's database ID
    """
    try:
        # Get paper
        result = await session.execute(
            select(ArxivModel).where(ArxivModel.id == paper_id)
        )
        paper = result.scalar_one_or_none()
        
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found"
            )
        
        # Convert to response format
        paper_dict = paper.to_dict()
        return PaperResponse(**paper_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting paper", paper_id=paper_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve paper"
        )


@router.post("/papers", response_model=PaperResponse, status_code=status.HTTP_201_CREATED, summary="Create new paper")
async def create_paper(
    paper_data: PaperCreate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Create a new ArXiv paper entry.
    
    Requires authentication. Only verified users can create papers.
    """
    try:
        # Check if user is verified (optional additional check)
        if not current_user.is_verified and current_user.papers_saved_count == 0:
            # Allow creation for new users, but could add stricter verification later
            pass
        
        # Check if paper already exists by ArXiv URL
        existing_result = await session.execute(
            select(ArxivModel).where(ArxivModel.arxiv_url == paper_data.arxiv_url)
        )
        existing_paper = existing_result.scalar_one_or_none()
        
        if existing_paper:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Paper with this ArXiv URL already exists"
            )
        
        # Create new paper
        from datetime import datetime
        paper = ArxivModel(
            title=paper_data.title,
            authors=paper_data.authors,
            abstract=paper_data.abstract,
            arxiv_url=paper_data.arxiv_url,
            pdf_url=paper_data.pdf_url,
            published_time=datetime.fromisoformat(paper_data.published_time.replace('Z', '+00:00')),
            journal_link=paper_data.journal_link,
            tag=paper_data.tag,
            popularity=0,
            analyzed=False
        )
        
        session.add(paper)
        await session.flush()  # Get the ID
        
        logger.info("Paper created", paper_id=paper.id, user_id=current_user.id)
        await session.commit()
        
        # Convert to response format
        paper_dict = paper.to_dict()
        return PaperResponse(**paper_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error creating paper", error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create paper"
        )


@router.put("/papers/{paper_id}", response_model=PaperResponse, summary="Update paper")
async def update_paper(
    paper_id: int,
    paper_data: PaperUpdate,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Update an existing ArXiv paper.
    
    Requires authentication. Users can update papers they created or if they're verified.
    """
    try:
        # Get paper
        result = await session.execute(
            select(ArxivModel).where(ArxivModel.id == paper_id)
        )
        paper = result.scalar_one_or_none()
        
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found"
            )
        
        # Check permissions (for now, allow any verified user to edit)
        # In the future, you might want to add ownership or role-based permissions
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only verified users can update papers"
            )
        
        # Update fields
        update_data = paper_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(paper, field, value)
        
        logger.info("Paper updated", paper_id=paper.id, user_id=current_user.id)
        await session.commit()
        
        # Convert to response format
        paper_dict = paper.to_dict()
        return PaperResponse(**paper_dict)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error updating paper", paper_id=paper_id, error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update paper"
        )


@router.delete("/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete paper")
async def delete_paper(
    paper_id: int,
    session: AsyncSession = Depends(get_async_session),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Delete an ArXiv paper.
    
    Requires authentication and verification. Only verified users can delete papers.
    """
    try:
        # Get paper
        result = await session.execute(
            select(ArxivModel).where(ArxivModel.id == paper_id)
        )
        paper = result.scalar_one_or_none()
        
        if not paper:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Paper not found"
            )
        
        # Check permissions (strict - only verified users)
        if not current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only verified users can delete papers"
            )
        
        # Delete paper
        await session.delete(paper)
        logger.info("Paper deleted", paper_id=paper.id, user_id=current_user.id)
        await session.commit()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting paper", paper_id=paper_id, error=str(e), user_id=current_user.id)
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete paper"
        ) 