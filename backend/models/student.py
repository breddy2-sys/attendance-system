"""Student model."""

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Student(Base):
    """Student model.
    
    Attributes:
        id: Primary key.
        user_id: Foreign key to User.
        roll_number: Unique student identification number.
        semester: Current semester (1-8).
        department_id: Foreign key to Department.
    """
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True
    )
    roll_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True
    )
    semester: Mapped[int] = mapped_column(Integer)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="student"
    )
    department: Mapped["Department"] = relationship(
        back_populates="students"
    )
    student_subjects: Mapped[list["StudentSubject"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan"
    )
    attendance_summaries: Mapped[list["AttendanceSummary"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan"
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        back_populates="student",
        cascade="all, delete-orphan"
    )
