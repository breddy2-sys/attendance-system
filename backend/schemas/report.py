"""Pydantic schemas for reporting."""

from pydantic import BaseModel, Field
from datetime import datetime, date


class AttendanceReportFilter(BaseModel):
    """Filter parameters for attendance reports."""
    subject_id: int | None = None
    department_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    zone: str | None = Field(
        None,
        description="Filter by zone: safe/warning/danger/critical"
    )


class SubjectReportRow(BaseModel):
    """Single row in subject attendance report."""
    student_id: int
    full_name: str
    roll_number: str
    classes_attended: int
    classes_held: int
    percentage: float
    zone: str


class SubjectAttendanceReport(BaseModel):
    """Subject-level attendance report."""
    subject_id: int
    subject_name: str
    faculty_name: str
    total_students: int
    average_percentage: float
    students_by_zone: dict = Field(
        default_factory=dict,
        description="{safe: count, warning: count, ...}"
    )
    rows: list[SubjectReportRow]


class DepartmentReportSummary(BaseModel):
    """Department-level summary."""
    department_id: int
    department_name: str
    total_students: int
    average_attendance: float
    zone_distribution: dict
    subjects: list[SubjectAttendanceReport]


class WeeklyReportSummary(BaseModel):
    """Weekly summary for faculty/admin."""
    week_start: date
    week_end: date
    total_sessions: int
    submitted_on_time: int
    late_submissions: int
    missing_submissions: int
    average_attendance: float
    zone_distribution: dict
    anomalies: list[dict]


class PDFReportRequest(BaseModel):
    """Request PDF report generation."""
    report_type: str = Field(
        ...,
        description="subject/department/weekly"
    )
    subject_id: int | None = None
    department_id: int | None = None
    start_date: date | None = None
    end_date: date | None = None


class ReportDownload(BaseModel):
    """Report download response."""
    report_id: int
    filename: str
    url: str
    file_type: str = Field(
        ...,
        description="pdf/csv"
    )
    generated_at: datetime
    expires_at: datetime
