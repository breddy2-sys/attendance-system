"""Threshold recommendation model (Agent 6 output)."""

from datetime import datetime
from enum import Enum
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, func, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class RecommendationStatus(str, Enum):
    """Recommendation status enumeration."""
    PENDING_ADMIN_REVIEW = "pending_admin_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class RecommendationType(str, Enum):
    """Type of threshold recommendation."""
    THRESHOLD_TOO_STRICT = "threshold_too_strict"
    THRESHOLD_TOO_LENIENT = "threshold_too_lenient"
    THRESHOLD_APPROPRIATE = "threshold_appropriate"
    NEEDS_REVIEW = "needs_review"


class ThresholdRecommendation(Base):
    """Agent 6 threshold optimizer recommendations.
    
    Attributes:
        id: Primary key.
        subject_id: FK to Subject being evaluated.
        current_threshold: Current threshold value.
        recommendation_type: Type of recommendation (strict/lenient/appropriate).
        supporting_data: JSON with zone distribution and stats.
        reason: Plain language reason for recommendation.
        status: pending_admin_review/approved/rejected.
        reviewed_by_id: FK to User (admin) if reviewed.
        created_at: When recommendation was generated.
    """
    __tablename__ = "threshold_recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True
    )
    current_threshold: Mapped[float] = mapped_column()
    recommendation_type: Mapped[str] = mapped_column(String(50))
    supporting_data: Mapped[dict] = mapped_column(JSON)
    reason: Mapped[str] = mapped_column(Text)
    status: Mapped[RecommendationStatus] = mapped_column(
        SQLEnum(RecommendationStatus),
        default=RecommendationStatus.PENDING_ADMIN_REVIEW
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    subject: Mapped["Subject"] = relationship(
        back_populates="threshold_recommendations"
    )
    reviewed_by: Mapped["User"] = relationship(
        back_populates="threshold_recommendations",
        foreign_keys=[reviewed_by_id]
    )
