"""User model with RBAC support."""

from datetime import datetime
from enum import Enum
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class UserRole(str, Enum):
    """Role enumeration for users."""
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "admin"


class User(Base):
    """User model for authentication and authorization.
    
    Attributes:
        id: Primary key.
        full_name: User's full name.
        email: Unique email address.
        hashed_password: Bcrypt hashed password.
        role: User role (student/faculty/admin).
        is_active: Account active status.
        created_at: Account creation timestamp.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole] = mapped_column(default=UserRole.STUDENT)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    student: Mapped["Student"] = relationship(back_populates="user")
    faculty: Mapped["Faculty"] = relationship(back_populates="user")
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="marked_by",
        foreign_keys="AttendanceRecord.marked_by_id"
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        back_populates="reviewed_by",
        foreign_keys="LeaveRequest.reviewed_by_id"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        back_populates="recipient"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user"
    )
    threshold_recommendations: Mapped[list["ThresholdRecommendation"]] = relationship(
        back_populates="reviewed_by",
        foreign_keys="ThresholdRecommendation.reviewed_by_id"
    )
