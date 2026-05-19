"""Weekly snapshot model (for historical trend tracking)."""

from datetime import datetime, date
from sqlalchemy import Date, Float, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class WeeklySnapshot(Base):
    """Weekly institution-wide attendance snapshot.
    
    Attributes:
        id: Primary key.
        week_start: Start date of the week.
        department_id: FK to Department (null = institution-wide).
        avg_attendance: Average attendance % for the week.
        zone_distribution: JSON with counts per zone.
        anomalies: JSON list of flagged anomalies.
        created_at: When snapshot was created.
    """
    __tablename__ = "weekly_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    week_start: Mapped[date] = mapped_column(Date, index=True)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    avg_attendance: Mapped[float] = mapped_column(Float)
    zone_distribution: Mapped[dict] = mapped_column(JSON)
    anomalies: Mapped[list] = mapped_column(JSON, default=[])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Relationships
    department: Mapped["Department"] = relationship(
        back_populates="weekly_snapshots"
    )
