"""Attendance session model (marks a class date for a subject)."""

from datetime import datetime
from sqlalchemy import Date, Text, DateTime, ForeignKey, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class AttendanceSession(Base):
    """Attendance session (per class per subject).
    
    Attributes:
        id: Primary key.
        subject_id: Foreign key to Subject.
        faculty_id: Foreign key to Faculty (who submitted).
        date: Date of the class.
        notes: Optional notes from faculty.
        submitted_at: When attendance was submitted.
    """
    __tablename__ = "attendance_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True
    )
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.id", ondelete="CASCADE"),
        index=True
    )
    date: Mapped[datetime] = mapped_column(
        Date,
        index=True
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    subject: Mapped["Subject"] = relationship(
        back_populates="attendance_sessions"
    )
    faculty: Mapped["Faculty"] = relationship(
        back_populates="attendance_sessions"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan"
    )
