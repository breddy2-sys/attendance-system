"""Pydantic schemas for agent operations."""

from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class AgentStatus(str, Enum):
    """Agent execution status."""
    IDLE = "idle"
    OBSERVING = "observing"
    THINKING = "thinking"
    PLANNING = "planning"
    ACTING = "acting"
    REFLECTING = "reflecting"
    DONE = "done"
    FAILED = "failed"


class AgentAuditLogResponse(BaseModel):
    """Agent audit log response."""
    id: int
    agent_name: str
    trigger_event: str
    trigger_data: dict
    observations: dict
    thoughts: list
    action_plan: list
    actions_taken: list
    reflection: str
    status: str
    started_at: datetime
    completed_at: datetime

    class Config:
        from_attributes = True


class AgentStatusResponse(BaseModel):
    """Current status of an agent."""
    agent_name: str
    last_run_at: datetime | None
    last_run_status: str | None
    times_run_today: int
    actions_taken_today: int
    next_scheduled_run: datetime | None


class AllAgentsStatus(BaseModel):
    """Status of all 6 agents."""
    watchdog: AgentStatusResponse
    recovery_advisor: AgentStatusResponse
    reminder: AgentStatusResponse
    leave_evaluator: AgentStatusResponse
    report_agent: AgentStatusResponse
    threshold_optimizer: AgentStatusResponse
    last_system_check: datetime


class AgentAuditLogFilter(BaseModel):
    """Filter parameters for agent logs."""
    agent_name: str | None = None
    trigger_event: str | None = None
    status: str | None = Field(
        None,
        description="done/failed"
    )
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int = Field(50, le=500)
    offset: int = Field(0, ge=0)


class PaginatedAgentLogs(BaseModel):
    """Paginated agent logs."""
    total: int
    limit: int
    offset: int
    logs: list[AgentAuditLogResponse]
