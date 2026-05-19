"""
Database models for College Attendance Monitoring System.
All models are async-compatible with SQLAlchemy 2.0+
"""

from backend.models.user import User
from backend.models.student import Student
from backend.models.faculty import Faculty
from backend.models.department import Department
from backend.models.subject import Subject
from backend.models.timetable import Timetable
from backend.models.student_subject import StudentSubject
from backend.models.attendance_session import AttendanceSession
from backend.models.attendance_record import AttendanceRecord
from backend.models.attendance_summary import AttendanceSummary
from backend.models.leave_request import LeaveRequest
from backend.models.notification import Notification
from backend.models.agent_audit_log import AgentAuditLog
from backend.models.threshold_recommendation import ThresholdRecommendation
from backend.models.weekly_snapshot import WeeklySnapshot
from backend.models.audit_log import AuditLog

__all__ = [
    "User",
    "Student",
    "Faculty",
    "Department",
    "Subject",
    "Timetable",
    "StudentSubject",
    "AttendanceSession",
    "AttendanceRecord",
    "AttendanceSummary",
    "LeaveRequest",
    "Notification",
    "AgentAuditLog",
    "ThresholdRecommendation",
    "WeeklySnapshot",
    "AuditLog",
]
