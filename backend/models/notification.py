"""Notification model (WebSocket-based, in-app only)."""

from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class NotificationType(str):
    """Notification type constants."""
    ZONE_DROP = "zone_drop"
    STREAK_ALERT = "streak_alert"
    EDGE_WARNING = "edge_warning"
    LEAVE_DECISION = "leave_decision"
    REMINDER = "reminder"
    URGENT_REMINDER = "urgent_reminder"
    ESCALATION = "escalation"
    WEEKLY_SUMMARY = "weekly_summary"
    THRESHOLD_REVIEW = "threshold_review"


class Notification(Base):
    """In-app WebSocket notification.
    
    Attributes:
        id: Primary key.
        recipient_id: FK to User (who receives).
        title: Notification title.
        message: Notification message body.
        type: Notification type (zone_drop, reminder, etc.).
        is_read: Whether user has read it.
        created_at: Creation timestamp.
    """
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    recipient_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    message: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(50))
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    recipient: Mapped["User"] = relationship(
        back_populates="notifications"
    )
