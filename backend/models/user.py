"""
User model for authentication and authorization.
Supports three roles: student, faculty, admin.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Integer, String
from sqlalchemy.orm import relationship

from backend.database import Base


class UserRole(str, Enum):
    """User role enumeration."""

    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"


class User(Base):
    """
    User model representing system users.

    Attributes:
        id: Primary key.
        full_name: User's full name.
        email: Unique email address.
        hashed_password: Bcrypt hashed password.
        role: User role (student/faculty/admin).
        is_active: Account activation status.
        created_at: Account creation timestamp.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    student = relationship("Student", back_populates="user", uselist=False)
    faculty = relationship("Faculty", back_populates="user", uselist=False)
    notifications = relationship("Notification", back_populates="recipient")
    attendance_records = relationship(
        "AttendanceRecord", foreign_keys="AttendanceRecord.marked_by_id"
    )
    leave_reviews = relationship(
        "LeaveRequest", foreign_keys="LeaveRequest.reviewed_by_id"
    )
    audit_logs = relationship("AuditLog", back_populates="user")

    def __repr__(self) -> str:
        """Return string representation."""
        return f"<User(id={self.id}, email={self.email}, role={self.role.value})>"
