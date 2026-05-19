"""Attendance record model (individual student attendance per session)."""

from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SQLEnum, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class AttendanceStatus(str, Enum):
    """Attendance status enumeration."""
    PRESENT = "present"
    ABSENT = "absent"
    LATE = "late"


class AttendanceRecord(Base):
    """Individual student attendance record.
    
    Attributes:
        id: Primary key.
        session_id: Foreign key to AttendanceSession.
        student_id: Foreign key to Student.
        status: Attendance status (present/absent/late).
        marked_by_id: Foreign key to User (who marked).
        created_at: Record creation timestamp.
    """
    __tablename__ = "attendance_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("attendance_sessions.id", ondelete="CASCADE"),
        index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True
    )
    status: Mapped[AttendanceStatus] = mapped_column(
        SQLEnum(AttendanceStatus),
        default=AttendanceStatus.PRESENT
    )
    marked_by_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    session: Mapped["AttendanceSession"] = relationship(
        back_populates="attendance_records"
    )
    student: Mapped["Student"] = relationship(
        back_populates="attendance_records"
    )
    marked_by: Mapped["User"] = relationship(
        back_populates="attendance_records",
        foreign_keys=[marked_by_id]
    )
