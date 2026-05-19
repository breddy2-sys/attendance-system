"""Pydantic schemas for attendance operations."""

from pydantic import BaseModel, Field
from datetime import datetime, date
from enum import Enum


class AttendanceStatus(str, Enum):
    """Attendance status enumeration."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class AttendanceRecordCreate(BaseModel):
    """Create attendance record schema."""
    student_id: int
    status: AttendanceStatus = AttendanceStatus.PRESENT


class AttendanceRecordResponse(BaseModel):
    """Attendance record response schema."""
    id: int
    session_id: int
    student_id: int
    status: AttendanceStatus
    created_at: datetime

    class Config:
        from_attributes = True


class AttendanceSessionCreate(BaseModel):
    """Create attendance session schema."""
    subject_id: int
    date: date
    notes: str | None = None
    records: list[AttendanceRecordCreate]


class AttendanceSessionResponse(BaseModel):
    """Attendance session response schema."""
    id: int
    subject_id: int
    faculty_id: int
    date: date
    notes: str | None
    submitted_at: datetime
    records: list[AttendanceRecordResponse] = []

    class Config:
        from_attributes = True


class AttendanceSessionPreview(BaseModel):
    """Preview of attendance changes before submission."""
    total_students: int
    present_count: int
    absent_count: int
    late_count: int
    zone_drops: list[dict] = Field(
        default_factory=list,
        description="Students whose zone will drop"
    )
    students_at_risk: int


class AttendanceSummaryResponse(BaseModel):
    """Attendance summary response (denormalized cache)."""
    id: int
    student_id: int
    subject_id: int
    classes_held: int
    classes_attended: int
    current_percentage: float
    zone: str
    classes_can_miss: int
    classes_needed: int
    trend: str
    last_updated: datetime

    class Config:
        from_attributes = True


class StudentAttendanceDetail(BaseModel):
    """Detailed attendance for single student per subject."""
    subject_id: int
    subject_name: str
    current_percentage: float
    zone: str
    classes_held: int
    classes_attended: int
    classes_can_miss: int
    classes_needed: int
    best_case_percentage: float
    worst_case_percentage: float
    trend: str
    threshold: float


class StudentFullAttendance(BaseModel):
    """Student's full attendance across all subjects."""
    student_id: int
    full_name: str
    roll_number: str
    semester: int
    subjects: list[StudentAttendanceDetail]
    overall_health_score: float
