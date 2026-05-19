"""StudentSubject association model (many-to-many)."""

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class StudentSubject(Base):
    """Association between students and subjects (enrollment).
    
    Attributes:
        id: Primary key.
        student_id: Foreign key to Student.
        subject_id: Foreign key to Subject.
    """
    __tablename__ = "student_subjects"
    __table_args__ = (
        UniqueConstraint("student_id", "subject_id", name="uix_student_subject"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        back_populates="student_subjects"
    )
    subject: Mapped["Subject"] = relationship(
        back_populates="student_subjects"
    )
