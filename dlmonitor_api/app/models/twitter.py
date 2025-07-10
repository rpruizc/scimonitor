"""
Twitter/X posts model using SQLAlchemy 2.0 with async support.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils.types import TSVectorType

from app.db.base import Base


class TwitterModel(Base):
    """
    Model for Twitter/X posts related to deep learning and AI research.
    
    Stores tweet metadata and search vectors for full-text search capabilities.
    """
    
    __tablename__ = "twitter"

    # Primary keys - both integer ID and Twitter ID for flexibility
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tweet_id: Mapped[str] = mapped_column(String(20), primary_key=True, unique=True)
    
    # Tweet content
    text: Mapped[str] = mapped_column(Text, nullable=False)
    user: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    
    # Media and attachments
    pic_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Publication information
    published_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Social metrics
    popularity: Mapped[int] = mapped_column(Integer, default=0, index=True)
    
    # Full-text search vector (PostgreSQL specific)
    search_vector: Mapped[Optional[str]] = mapped_column(
        TSVectorType('text'),
        nullable=True
    )

    # Database indexes for performance
    __table_args__ = (
        Index('ix_twitter_published_popularity', 'published_time', 'popularity'),
        Index('ix_twitter_user_published', 'user', 'published_time'),
    )

    def __repr__(self) -> str:
        """String representation of the Twitter post."""
        text_preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        return f"<TwitterModel(id={self.id}, user='{self.user}', text='{text_preview}')>"
    
    @property
    def short_text(self) -> str:
        """Get truncated text for display purposes."""
        return self.text[:200] + "..." if len(self.text) > 200 else self.text
    
    @property
    def twitter_url(self) -> str:
        """Generate Twitter URL for this tweet."""
        return f"https://twitter.com/{self.user}/status/{self.tweet_id}"
    
    @property
    def has_media(self) -> bool:
        """Check if tweet has media attachments."""
        return bool(self.pic_url)
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "tweet_id": self.tweet_id,
            "text": self.text,
            "user": self.user,
            "pic_url": self.pic_url,
            "published_time": self.published_time.isoformat(),
            "popularity": self.popularity,
            "twitter_url": self.twitter_url,
            "has_media": self.has_media,
        } 