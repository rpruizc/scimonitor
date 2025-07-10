"""
Working queue model for background job processing using SQLAlchemy 2.0.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, DateTime, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class WorkingQueueModel(Base):
    """
    Model for background job queue management.
    
    Stores jobs for async processing like PDF analysis, 
    content fetching, and AI processing tasks.
    """
    
    __tablename__ = "working"

    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Job information
    type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    param: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Timestamps (enhanced from legacy model)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Job status and priority
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False, index=True)
    
    # Error handling
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    # Database indexes for performance
    __table_args__ = (
        Index('ix_working_type_status', 'type', 'status'),
        Index('ix_working_status_priority', 'status', 'priority'),
        Index('ix_working_created_status', 'created_at', 'status'),
    )

    def __repr__(self) -> str:
        """String representation of the working queue job."""
        return f"<WorkingQueueModel(id={self.id}, type='{self.type}', status='{self.status}', param='{self.param}')>"
    
    @property
    def is_pending(self) -> bool:
        """Check if job is pending execution."""
        return self.status == "pending"
    
    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == "running"
    
    @property
    def is_completed(self) -> bool:
        """Check if job has completed successfully."""
        return self.status == "completed"
    
    @property
    def is_failed(self) -> bool:
        """Check if job has failed."""
        return self.status == "failed"
    
    @property
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return self.attempts < self.max_attempts and self.is_failed
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate job duration in seconds if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def mark_started(self) -> None:
        """Mark job as started."""
        self.status = "running"
        self.started_at = datetime.utcnow()
        self.attempts += 1
    
    def mark_completed(self) -> None:
        """Mark job as completed successfully."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        self.error_message = None
    
    def mark_failed(self, error_message: str) -> None:
        """Mark job as failed with error message."""
        self.status = "failed"
        self.completed_at = datetime.utcnow()
        self.error_message = error_message[:1000]  # Truncate if too long
    
    def to_dict(self) -> dict:
        """Convert model to dictionary for API responses."""
        return {
            "id": self.id,
            "type": self.type,
            "param": self.param,
            "status": self.status,
            "priority": self.priority,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "can_retry": self.can_retry,
        } 