"""Base agent class implementing Observe→Think→Plan→Act→Reflect loop.

All 6 agents inherit from this base class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import json
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    OBSERVING = "observing"
    THINKING = "thinking"
    PLANNING = "planning"
    ACTING = "acting"
    REFLECTING = "reflecting"
    DONE = "done"
    FAILED = "failed"


@dataclass
class AgentContext:
    """Context for agent execution."""
    trigger_event: str
    trigger_data: dict
    observations: dict = field(default_factory=dict)
    thoughts: list = field(default_factory=list)
    action_plan: list = field(default_factory=list)
    actions_taken: list = field(default_factory=list)
    reflection: str = ""
    status: AgentStatus = AgentStatus.IDLE
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class BaseAgent(ABC):
    """Base agent implementing standard agentic loop."""

    name: str = "BaseAgent"

    def __init__(self, db: AsyncSession):
        """Initialize agent with database session.

        Args:
            db: Async database session.
        """
        self.db = db

    async def run(
        self,
        trigger_event: str,
        trigger_data: dict,
    ) -> AgentContext:
        """Execute full agent loop: Observe→Think→Plan→Act→Reflect.

        Args:
            trigger_event: Event name that triggered agent.
            trigger_data: Event data/payload.

        Returns:
            AgentContext with full execution details.
        """
        ctx = AgentContext(
            trigger_event=trigger_event,
            trigger_data=trigger_data,
        )

        try:
            # OBSERVE
            ctx.status = AgentStatus.OBSERVING
            logger.info(f"[{self.name}] OBSERVE phase starting...")
            ctx.observations = await self.observe(ctx)
            logger.info(f"[{self.name}] Observations: {len(ctx.observations)} items")

            # THINK
            ctx.status = AgentStatus.THINKING
            logger.info(f"[{self.name}] THINK phase starting...")
            ctx.thoughts = await self.think(ctx)
            logger.info(f"[{self.name}] Generated {len(ctx.thoughts)} insights")

            # PLAN
            ctx.status = AgentStatus.PLANNING
            logger.info(f"[{self.name}] PLAN phase starting...")
            ctx.action_plan = await self.plan(ctx)
            logger.info(f"[{self.name}] Planned {len(ctx.action_plan)} actions")

            # ACT
            ctx.status = AgentStatus.ACTING
            logger.info(f"[{self.name}] ACT phase starting...")
            ctx.actions_taken = await self.act(ctx)
            logger.info(f"[{self.name}] Executed {len(ctx.actions_taken)} actions")

            # REFLECT
            ctx.status = AgentStatus.REFLECTING
            logger.info(f"[{self.name}] REFLECT phase starting...")
            ctx.reflection = await self.reflect(ctx)

            ctx.status = AgentStatus.DONE
            ctx.completed_at = datetime.utcnow()
            logger.info(f"[{self.name}] DONE: {ctx.reflection}")

        except Exception as e:
            ctx.status = AgentStatus.FAILED
            ctx.reflection = f"Agent failed: {str(e)}"
            ctx.completed_at = datetime.utcnow()
            logger.error(
                f"[{self.name}] Failed in {ctx.status.value} phase: {e}",
                exc_info=True,
            )
        finally:
            await self.log_to_audit(ctx)

        return ctx

    @abstractmethod
    async def observe(self, ctx: AgentContext) -> dict:
        """OBSERVE: Load all relevant data for decision making.

        Args:
            ctx: Agent context.

        Returns:
            Dictionary of observations.
        """
        pass

    @abstractmethod
    async def think(self, ctx: AgentContext) -> list[str]:
        """THINK: Analyze observations, generate insights.

        Args:
            ctx: Agent context with observations.

        Returns:
            List of insight strings.
        """
        pass

    @abstractmethod
    async def plan(self, ctx: AgentContext) -> list[dict]:
        """PLAN: Build ordered action list from insights.

        Args:
            ctx: Agent context with thoughts.

        Returns:
            List of action plan dictionaries.
        """
        pass

    @abstractmethod
    async def act(self, ctx: AgentContext) -> list[dict]:
        """ACT: Execute all planned actions.

        Args:
            ctx: Agent context with action plan.

        Returns:
            List of executed action results.
        """
        pass

    @abstractmethod
    async def reflect(self, ctx: AgentContext) -> str:
        """REFLECT: Summarize what was done and outcome.

        Args:
            ctx: Agent context with all execution data.

        Returns:
            Reflection summary string.
        """
        pass

    async def log_to_audit(self, ctx: AgentContext) -> None:
        """Persist agent execution to agent_audit_logs table.

        Args:
            ctx: Agent context to persist.
        """
        try:
            from backend.models.agent_audit_log import AgentAuditLog

            log = AgentAuditLog(
                agent_name=self.name,
                trigger_event=ctx.trigger_event,
                trigger_data=ctx.trigger_data,
                observations=ctx.observations,
                thoughts=ctx.thoughts,
                action_plan=ctx.action_plan,
                actions_taken=ctx.actions_taken,
                reflection=ctx.reflection,
                status=ctx.status.value,
                started_at=ctx.started_at,
                completed_at=ctx.completed_at or datetime.utcnow(),
            )
            self.db.add(log)
            await self.db.commit()
            logger.info(f"[{self.name}] Audit log persisted")

        except Exception as e:
            logger.error(f"[{self.name}] Error logging to audit: {e}")
            # Don't re-raise - audit failure shouldn't break agent
