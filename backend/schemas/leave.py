"""Pydantic schemas for leave operations."""

from pydantic import BaseModel, Field
from datetime import date, datetime
from enum import Enum


class LeaveStatus(str, Enum):
    """Leave status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"


class LeaveDecision(str, Enum):
    """AI decision type."""
    AUTO_APPROVE = "auto_approve"
    CONDITIONAL_APPROVE = "conditional_approve"
    FLAG_FOR_REVIEW = "flag_for_review"
    AUTO_REJECT = "auto_reject"


class LeaveRequestCreate(BaseModel):
    """Create leave request schema."""
    subject_id: int
    start_date: date
    end_date: date
    reason: str = Field(..., min_length=10, max_length=1000)


class LeaveRequestPreview(BaseModel):
    """Preview leave request impact before submission."""
    current_percentage: float
    new_percentage: float
    classes_missing: int
    classes_remaining_after: int
    recovery_possible: bool
    impact_message: str


class LeaveRequestResponse(BaseModel):
    """Leave request response schema."""
    id: int
    student_id: int
    subject_id: int
    subject_name: str
    start_date: date
    end_date: date
    reason: str
    status: LeaveStatus
    ai_decision: str
    ai_reasoning: str
    attendance_impact_pct: float | None
    reviewed_by_id: int | None
    reviewed_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class LeaveRequestUpdate(BaseModel):
    """Update leave request (faculty review)."""
    status: LeaveStatus
    ai_reasoning: str | None = None


class LeaveHistory(BaseModel):
    """Student's leave history."""
    total_requests: int
    approved: int
    rejected: int
    pending: int
    requests: list[LeaveRequestResponse]
