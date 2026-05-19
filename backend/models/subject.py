"""Subject model."""

from sqlalchemy import String, Float, Integer, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Subject(Base):
    """Subject/Course model.
    
    Attributes:
        id: Primary key.
        name: Subject name.
        code: Subject code (unique).
        department_id: Foreign key to Department.
        faculty_id: Foreign key to Faculty (instructor).
        attendance_threshold: Default threshold percentage (0-100).
        total_planned_classes: Expected classes for semester.
        semester: Semester number (1-8).
        is_active: Whether subject is currently active.
    """
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        index=True
    )
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculty.id", ondelete="SET NULL"),
        nullable=True
    )
    attendance_threshold: Mapped[float] = mapped_column(Float, default=75.0)
    total_planned_classes: Mapped[int] = mapped_column(Integer, default=40)
    semester: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    department: Mapped["Department"] = relationship(
        back_populates="subjects"
    )
    faculty: Mapped["Faculty"] = relationship(
        back_populates="subjects"
    )
    timetables: Mapped[list["Timetable"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan"
    )
    student_subjects: Mapped[list["StudentSubject"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan"
    )
    attendance_sessions: Mapped[list["AttendanceSession"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan"
    )
    attendance_summaries: Mapped[list["AttendanceSummary"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan"
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan"
    )
    threshold_recommendations: Mapped[list["ThresholdRecommendation"]] = relationship(
        back_populates="subject",
        cascade="all, delete-orphan"
    )
