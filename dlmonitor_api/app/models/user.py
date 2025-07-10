"""
User model for DLMonitor application.
Links to Supabase Auth and stores user preferences.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, DateTime, Boolean, Integer, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserModel(Base):
    """
    User model linked to Supabase authentication.
    
    Stores user preferences, research interests, and application-specific data
    while delegating authentication to Supabase.
    """
    
    __tablename__ = "users"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Supabase integration
    supabase_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email_confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Profile information
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # OAuth provider info
    auth_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    github_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    github_avatar: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Research profile
    research_interests: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    affiliation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    orcid_id: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    
    # User preferences (stored as JSON)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, index=True)
    
    # Usage statistics
    papers_saved_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    searches_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships (to be defined when creating related models)
    # saved_papers = relationship("SavedPaper", back_populates="user")
    # search_history = relationship("SearchHistory", back_populates="user")
    # user_preferences = relationship("UserPreference", back_populates="user")

    # Database indexes for performance
    __table_args__ = (
        Index('ix_user_provider_github', 'auth_provider', 'github_username'),
        Index('ix_user_active_created', 'is_active', 'created_at'),
        Index('ix_user_verified_active', 'is_verified', 'is_active'),
    )

    def __repr__(self) -> str:
        """String representation of the user."""
        return f"<UserModel(id={self.id}, email='{self.email}', supabase_id='{self.supabase_id}')>"
    
    @property
    def display_name(self) -> str:
        """Get the best available display name for the user."""
        return self.full_name or self.github_username or self.email.split("@")[0]
    
    @property
    def is_github_user(self) -> bool:
        """Check if user authenticated via GitHub."""
        return self.auth_provider == "github" and bool(self.github_username)
    
    @property
    def profile_image(self) -> Optional[str]:
        """Get the best available profile image URL."""
        return self.github_avatar or self.avatar_url
    
    def update_last_login(self) -> None:
        """Update last login timestamp."""
        self.last_login_at = datetime.utcnow()
    
    def increment_papers_saved(self) -> None:
        """Increment saved papers count."""
        self.papers_saved_count += 1
    
    def increment_searches(self) -> None:
        """Increment searches count."""
        self.searches_count += 1
    
    def update_preferences(self, new_preferences: dict) -> None:
        """Update user preferences (merge with existing)."""
        if self.preferences:
            self.preferences.update(new_preferences)
        else:
            self.preferences = new_preferences
        self.updated_at = datetime.utcnow()
    
    def get_preference(self, key: str, default=None):
        """Get a specific preference value."""
        return self.preferences.get(key, default) if self.preferences else default
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "supabase_id": self.supabase_id,
            "email": self.email,
            "email_confirmed": self.email_confirmed,
            "full_name": self.full_name,
            "display_name": self.display_name,
            "avatar_url": self.profile_image,
            "auth_provider": self.auth_provider,
            "github_username": self.github_username,
            "research_interests": self.research_interests,
            "affiliation": self.affiliation,
            "orcid_id": self.orcid_id,
            "preferences": self.preferences,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "papers_saved_count": self.papers_saved_count,
            "searches_count": self.searches_count,
        }
    
    def to_public_dict(self) -> dict:
        """Convert model to dictionary for public API responses (limited fields)."""
        return {
            "id": self.id,
            "display_name": self.display_name,
            "avatar_url": self.profile_image,
            "github_username": self.github_username if self.is_github_user else None,
            "affiliation": self.affiliation,
            "research_interests": self.research_interests,
            "created_at": self.created_at.isoformat(),
        } 