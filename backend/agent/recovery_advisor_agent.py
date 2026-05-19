"""Agent 2: Recovery Advisor Agent - Generates personalized guidance.

Trigger: When student opens dashboard or calls GET /guidance/student/{id}
Runs: Synchronously in request handler

Observe → Load student's subjects, attendance summaries, timetable
Think   → Calculate health score, trend, identify urgent subjects
Plan    → Sort by urgency, generate per-subject guidance
Act     → Generate GuidanceResult with all calculations
Reflect → Log health metrics
"""

import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.base_agent import BaseAgent, AgentContext
from backend.models.student import Student
from backend.services.guidance_service import GuidanceService
from backend.schemas.guidance import GuidanceResult

logger = logging.getLogger(__name__)


class RecoveryAdvisorAgent(BaseAgent):
    """Agent 2: Recovery Advisor - Generates personalized guidance."""

    name = "RecoveryAdvisorAgent"

    async def observe(self, ctx: AgentContext) -> dict:
        """Load student's attendance data.

        Expected trigger_data: {"student_id": int}
        """
        student_id = ctx.trigger_data.get("student_id")

        # Load student
        student_result = await self.db.execute(
            select(Student).filter(Student.id == student_id)
        )
        student = student_result.scalar()

        if not student:
            return {"error": f"Student {student_id} not found"}

        return {
            "student_id": student_id,
            "student_name": student.user.full_name if student.user else "Unknown",
        }

    async def think(self, ctx: AgentContext) -> list[str]:
        """Generate insights about student's status."""
        insights = [
            "Loading student's attendance across all subjects",
            "Calculating overall health score",
            "Identifying urgent subjects requiring intervention",
            "Detecting attendance trends (improving/declining/stable)",
        ]
        return insights

    async def plan(self, ctx: AgentContext) -> list[dict]:
        """Plan guidance generation."""
        return [
            {
                "type": "generate_guidance",
                "description": "Generate complete guidance result using GuidanceService",
            }
        ]

    async def act(self, ctx: AgentContext) -> list[dict]:
        """Generate guidance using GuidanceService."""
        student_id = ctx.observations.get("student_id")

        try:
            guidance_service = GuidanceService()
            guidance_result = await guidance_service.get_student_guidance(
                self.db, student_id
            )

            return [
                {
                    "type": "guidance_generated",
                    "health_score": guidance_result.overall_health_score,
                    "subjects_analyzed": len(guidance_result.subjects_by_priority),
                    "guidance_result": guidance_result,
                }
            ]
        except Exception as e:
            logger.error(f"Error generating guidance: {e}")
            return [{"type": "guidance_failed", "error": str(e)}]

    async def reflect(self, ctx: AgentContext) -> str:
        """Summarize guidance generation."""
        actions = ctx.actions_taken
        if actions and actions[0]["type"] == "guidance_generated":
            health_score = actions[0].get("health_score", 0)
            subjects = actions[0].get("subjects_analyzed", 0)
            return (
                f"Recovery Advisor: Generated guidance with health score {health_score}. "
                f"Analyzed {subjects} subjects."
            )
        else:
            return "Recovery Advisor: Guidance generation failed."
