"""Leave request model (for student absence management)."""

from datetime import datetime, date
from enum import Enum
from sqlalchemy import Date, Text, Float, DateTime, ForeignKey, JSON, func, Enum as SQLEnum
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class LeaveStatus(str, Enum):
    """Leave request status enumeration."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONDITIONAL = "conditional"


class LeaveDecision(str, Enum):
    """AI agent decision types."""
    AUTO_APPROVE = "auto_approve"
    CONDITIONAL_APPROVE = "conditional_approve"
    FLAG_FOR_REVIEW = "flag_for_review"
    AUTO_REJECT = "auto_reject"


class LeaveRequest(Base):
    """Leave request with AI agent evaluation.
    
    Attributes:
        id: Primary key.
        student_id: Foreign key to Student.
        subject_id: Foreign key to Subject.
        start_date: Leave start date.
        end_date: Leave end date.
        dates: JSONB array of specific dates (if not continuous).
        reason: Reason for leave.
        attendance_impact_pct: Projected attendance % if approved.
        ai_decision: Agent 4 decision (auto_approve/conditional/reject).
        ai_reasoning: Agent 4 reasoning text.
        status: Final status (pending/approved/rejected/conditional).
        reviewed_by_id: FK to User (faculty reviewer if flagged).
        reviewed_at: When faculty reviewed (if applicable).
    """
    __tablename__ = "leave_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"),
        index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"),
        index=True
    )
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    dates: Mapped[list | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str] = mapped_column(Text)
    attendance_impact_pct: Mapped[float | None] = mapped_column(
        Float,
        nullable=True
    )
    ai_decision: Mapped[str] = mapped_column(String(50))
    ai_reasoning: Mapped[str] = mapped_column(Text)
    status: Mapped[LeaveStatus] = mapped_column(
        SQLEnum(LeaveStatus),
        default=LeaveStatus.PENDING
    )
    reviewed_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    student: Mapped["Student"] = relationship(
        back_populates="leave_requests"
    )
    subject: Mapped["Subject"] = relationship(
        back_populates="leave_requests"
    )
    reviewed_by: Mapped["User"] = relationship(
        back_populates="leave_requests",
        foreign_keys=[reviewed_by_id]
    )
