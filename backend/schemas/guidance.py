"""Pydantic schemas for guidance operations."""

from pydantic import BaseModel, Field
from datetime import datetime


class SubjectGuidance(BaseModel):
    """Guidance for single subject (from Agent 2)."""
    subject_id: int
    subject_name: str
    zone: str
    current_percentage: float
    threshold: float
    classes_held: int
    classes_attended: int
    classes_can_miss: int = 0
    classes_needed: int = 0
    projected_best: float
    projected_worst: float
    message: str = Field(
        ...,
        description="Template-based guidance message"
    )
    action: str = Field(
        ...,
        description="Recommended action"
    )
    urgency_rank: int = Field(
        ...,
        description="1=critical, 2=danger, 3=warning, 4=safe"
    )
    trend: str = Field(
        ...,
        description="improving/declining/stable"
    )


class GuidanceResult(BaseModel):
    """Complete guidance from Agent 2 Recovery Advisor."""
    overall_health_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Weighted health score 0-100"
    )
    subjects_by_priority: list[SubjectGuidance]
    top_priority_message: str = Field(
        ...,
        description="Most urgent action for student"
    )
    safe_subjects_count: int
    at_risk_subjects_count: int
    generated_at: datetime


class GuidanceMessage(BaseModel):
    """Template-based guidance message."""
    zone: str
    student_name: str
    subject_name: str
    current_percentage: float
    threshold: float
    can_miss: int = 0
    classes_needed: int = 0
    message: str
    action: str
