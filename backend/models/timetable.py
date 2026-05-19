"""Timetable model."""

from datetime import time
from sqlalchemy import String, Time, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Timetable(Base):
    """Class timetable/schedule model.
    
    Attributes:
        id: Primary key.
        subject_id: Foreign key to Subject.
        day_of_week: Day name (Monday, Tuesday, etc.).
        start_time: Class start time.
        end_time: Class end time.
        room: Room/classroom number.
        is_active: Whether schedule is active.
    """
    __tablename__ = "timetable"

    id: Mapped[int] = mapped_column(primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True
    )
    day_of_week: Mapped[str] = mapped_column(
        String(20),
        index=True
    )
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    room: Mapped[str] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    subject: Mapped["Subject"] = relationship(
        back_populates="timetables"
    )
