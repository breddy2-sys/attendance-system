"""Agent audit log model (tracks all 6 agent decisions)."""

from datetime import datetime
from sqlalchemy import String, Text, DateTime, JSON, func
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()


class AgentAuditLog(Base):
    """Complete audit log of agent execution.
    
    Attributes:
        id: Primary key.
        agent_name: Name of agent (watchdog, recovery_advisor, etc.).
        trigger_event: Event that triggered agent (attendance_submitted, etc.).
        trigger_data: JSON data that triggered agent.
        observations: JSON of observations made by agent.
        thoughts: JSON list of insights from thinking phase.
        action_plan: JSON list of planned actions.
        actions_taken: JSON list of actions executed.
        reflection: Summary text of what happened and outcome.
        status: Final status (done/failed).
        started_at: When agent started.
        completed_at: When agent completed.
    """
    __tablename__ = "agent_audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    agent_name: Mapped[str] = mapped_column(String(100), index=True)
    trigger_event: Mapped[str] = mapped_column(String(100), index=True)
    trigger_data: Mapped[dict] = mapped_column(JSON)
    observations: Mapped[dict] = mapped_column(JSON, default={})
    thoughts: Mapped[list] = mapped_column(JSON, default=[])
    action_plan: Mapped[list] = mapped_column(JSON, default=[])
    actions_taken: Mapped[list] = mapped_column(JSON, default=[])
    reflection: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(50), index=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
