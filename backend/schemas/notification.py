"""Pydantic schemas for notifications."""

from pydantic import BaseModel, Field
from datetime import datetime


class NotificationCreate(BaseModel):
    """Create notification schema."""
    recipient_id: int
    title: str = Field(..., max_length=255)
    message: str
    type: str = Field(
        ...,
        description="Type: zone_drop, reminder, leave_decision, etc."
    )


class NotificationResponse(BaseModel):
    """Notification response schema."""
    id: int
    recipient_id: int
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationList(BaseModel):
    """List of notifications."""
    notifications: list[NotificationResponse]
    unread_count: int
    total_count: int


class NotificationMarkRead(BaseModel):
    """Mark notification as read."""
    is_read: bool = True


class BulkNotificationCreate(BaseModel):
    """Create multiple notifications."""
    recipient_ids: list[int]
    title: str = Field(..., max_length=255)
    message: str
    type: str
