"""Attendance summary model (denormalized cache for fast queries)."""

from datetime import datetime
from sqlalchemy import Integer, Float, String, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class AttendanceZone(str):
    """Zone classification constants."""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"
    CRITICAL = "critical"


class AttendanceTrend(str):
    """Trend direction constants."""
    IMPROVING = "improving"
    DECLINING = "declining"
    STABLE = "stable"


class AttendanceSummary(Base):
    """Denormalized attendance summary (cached for performance).
    
    CRITICAL: This table is updated on every attendance_record change.
    Always call update_attendance_summary() after any record insert/update.
    
    Attributes:
        id: Primary key.
        student_id: Foreign key to Student.
        subject_id: Foreign key to Subject.
        classes_held: Total classes held for this subject.
        classes_attended: Classes attended by student.
        current_percentage: Current attendance percentage.
        zone: Current zone (safe/warning/danger/critical).
        classes_can_miss: How many can be missed while staying safe.
        classes_needed: How many needed to reach threshold.
        trend: Attendance trend direction.
        last_updated: Last update timestamp.
    """
    __tablename__ = "attendance_summary"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True
    )
    classes_held: Mapped[int] = mapped_column(Integer, default=0)
    classes_attended: Mapped[int] = mapped_column(Integer, default=0)
    current_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    zone: Mapped[str] = mapped_column(String(20), default=AttendanceZone.SAFE)
    classes_can_miss: Mapped[int] = mapped_column(Integer, default=0)
    classes_needed: Mapped[int] = mapped_column(Integer, default=0)
    trend: Mapped[str] = mapped_column(
        String(20),
        default=AttendanceTrend.STABLE
    )
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        back_populates="attendance_summaries"
    )
    subject: Mapped["Subject"] = relationship(
        back_populates="attendance_summaries"
    )
