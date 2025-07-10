"""
ArXiv papers model using SQLAlchemy 2.0 with async support.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Boolean, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils.types import TSVectorType

from app.db.base import Base


class ArxivModel(Base):
    """
    Model for ArXiv research papers.
    
    Stores paper metadata, content analysis, and search vectors
    for full-text search capabilities.
    """
    
    __tablename__ = "arxiv"

    # Primary keys - both integer ID and ArXiv URL for flexibility
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    arxiv_url: Mapped[str] = mapped_column(String(255), primary_key=True, unique=True)
    
    # Paper metadata
    version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(800), nullable=False, index=True)
    authors: Mapped[str] = mapped_column(String(800), nullable=False, index=True)
    abstract: Mapped[str] = mapped_column(Text, nullable=False)
    pdf_url: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Publication information
    published_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    journal_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tag: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    
    # Content analysis (populated by PDF analyzer)
    introduction: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    conclusion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    analyzed: Mapped[bool] = mapped_column(Boolean, default=False, server_default='false', index=True)
    
    # Social metrics
    popularity: Mapped[int] = mapped_column(Integer, default=0, index=True)
    
    # Full-text search vector (PostgreSQL specific)
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVectorType('title', 'abstract', 'authors', weights={'title': 'A', 'abstract': 'B', 'authors': 'C'}),
        nullable=True
    )

    # Database indexes for performance
    __table_args__ = (
        Index('ix_arxiv_published_popularity', 'published_time', 'popularity'),
        Index('ix_arxiv_analyzed_published', 'analyzed', 'published_time'),
    )

    def __repr__(self) -> str:
        """String representation of the ArXiv paper."""
        return f"<ArxivModel(id={self.id}, title='{self.title[:50]}...', published={self.published_time.date()})>"
    
    @property
    def short_title(self) -> str:
        """Get truncated title for display purposes."""
        return self.title[:100] + "..." if len(self.title) > 100 else self.title
    
    @property
    def author_list(self) -> list[str]:
        """Get list of authors from the comma-separated string."""
        return [author.strip() for author in self.authors.split(",") if author.strip()]
    
    @property
    def arxiv_id(self) -> str:
        """Extract ArXiv ID from URL."""
        # URL format: http://arxiv.org/abs/2301.12345
        return self.arxiv_url.split("/")[-1] if self.arxiv_url else ""
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "arxiv_id": self.arxiv_id,
            "arxiv_url": self.arxiv_url,
            "pdf_url": self.pdf_url,
            "title": self.title,
            "authors": self.author_list,
            "abstract": self.abstract,
            "published_time": self.published_time.isoformat(),
            "journal_link": self.journal_link,
            "tags": self.tag.split(" | ") if self.tag else [],
            "popularity": self.popularity,
            "analyzed": self.analyzed,
            "introduction": self.introduction,
            "conclusion": self.conclusion,
            "version": self.version,
        } 