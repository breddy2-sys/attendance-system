"""Faculty model."""

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Faculty(Base):
    """Faculty/Instructor model.
    
    Attributes:
        id: Primary key.
        user_id: Foreign key to User.
        employee_id: Unique employee identification number.
        department_id: Foreign key to Department.
    """
    __tablename__ = "faculty"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True
    )
    employee_id: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"),
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="faculty"
    )
    department: Mapped["Department"] = relationship(
        back_populates="faculty"
    )
    subjects: Mapped[list["Subject"]] = relationship(
        back_populates="faculty"
    )
    attendance_sessions: Mapped[list["AttendanceSession"]] = relationship(
        back_populates="faculty",
        cascade="all, delete-orphan"
    )
