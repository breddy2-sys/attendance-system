"""Department model."""

from sqlalchemy import String
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class Department(Base):
    """Department model.
    
    Attributes:
        id: Primary key.
        name: Department name.
        code: Department code (unique).
    """
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)

    # Relationships
    subjects: Mapped[list["Subject"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan"
    )
    faculty: Mapped[list["Faculty"]] = relationship(
        back_populates="department"
    )
    students: Mapped[list["Student"]] = relationship(
        back_populates="department"
    )
    weekly_snapshots: Mapped[list["WeeklySnapshot"]] = relationship(
        back_populates="department",
        cascade="all, delete-orphan"
    )
