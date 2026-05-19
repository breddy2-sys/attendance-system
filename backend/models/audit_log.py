"""System audit log model (for compliance & debugging)."""

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column, relationship

Base = declarative_base()


class AuditLog(Base):
    """System-wide audit log for compliance.
    
    Attributes:
        id: Primary key.
        user_id: FK to User who performed action.
        action: Action performed (create/update/delete).
        entity_type: Type of entity (student/subject/attendance).
        entity_id: ID of affected entity.
        old_value: JSON of old value (for updates).
        new_value: JSON of new value (for updates/creates).
        ip_address: IP address of requester.
        timestamp: When action occurred.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    action: Mapped[str] = mapped_column(String(50), index=True)
    entity_type: Mapped[str] = mapped_column(String(100), index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    old_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True
    )

    # Relationships
    user: Mapped["User"] = relationship(
        back_populates="audit_logs"
    )
