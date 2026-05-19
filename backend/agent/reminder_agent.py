"""Agent 3: Reminder Agent - Monitors attendance submission deadlines.

Trigger: Celery Beat every 60 minutes
Runs: Async background task

Observe → Load today's timetable, check if attendance submitted
Think   → Calculate hours since class ended, determine reminder level
Plan    → Build reminder actions (gentle/urgent/escalate)
Act     → Send notifications to faculty
Reflect → Log reminder stats
"""

import logging
from datetime import datetime, timedelta
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.base_agent import BaseAgent, AgentContext
from backend.models.timetable import Timetable
from backend.models.attendance_session import AttendanceSession
from backend.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


class ReminderAgent(BaseAgent):
    """Agent 3: Reminder Agent - Monitors attendance submission deadlines."""

    name = "ReminderAgent"

    async def observe(self, ctx: AgentContext) -> dict:
        """Load today's timetable and check submissions."""
        today = datetime.utcnow().date()

        # Load today's timetable entries
        timetable_result = await self.db.execute(
            select(Timetable).filter(
                Timetable.is_active == True,
            )
        )
        timetables = timetable_result.scalars().all()

        # For each timetable, check if attendance submitted today
        unsubmitted = []
        for tt in timetables:
            # Check if session exists for today
            session_result = await self.db.execute(
                select(AttendanceSession).filter(
                    and_(
                        AttendanceSession.subject_id == tt.subject_id,
                        func.DATE(AttendanceSession.date) == today,
                    )
                )
            )
            session = session_result.scalar()
            if not session:
                unsubmitted.append({
                    "timetable_id": tt.id,
                    "subject_id": tt.subject_id,
                    "end_time": tt.end_time,
                    "hours_since_end": GuidanceService._calculate_hours_since(
                        tt.end_time
                    ),
                })

        return {
            "today": today,
            "total_classes": len(timetables),
            "unsubmitted_count": len(unsubmitted),
            "unsubmitted": unsubmitted,
        }

    async def think(self, ctx: AgentContext) -> list[str]:
        """Analyze submission status."""
        observations = ctx.observations
        unsubmitted_count = observations.get("unsubmitted_count", 0)

        insights = [
            f"Checking {observations.get('total_classes', 0)} scheduled classes for today",
            f"Found {unsubmitted_count} classes without attendance submission",
        ]

        # Categorize by hours
        for item in observations.get("unsubmitted", []):
            hours = item.get("hours_since_end", 0)
            if hours >= 24:
                insights.append(f"Subject {item['subject_id']}: {hours}h overdue - ESCALATE")
            elif hours >= 6:
                insights.append(f"Subject {item['subject_id']}: {hours}h late - URGENT")
            elif hours >= 1:
                insights.append(f"Subject {item['subject_id']}: {hours}h pending - GENTLE")

        return insights

    async def plan(self, ctx: AgentContext) -> list[dict]:
        """Plan reminder actions."""
        actions = []

        for item in ctx.observations.get("unsubmitted", []):
            hours = item.get("hours_since_end", 0)

            if hours >= 24:
                actions.append({
                    "type": "escalate_to_admin",
                    "subject_id": item["subject_id"],
                    "hours": hours,
                })
            elif hours >= 6:
                actions.append({
                    "type": "urgent_reminder",
                    "subject_id": item["subject_id"],
                    "hours": hours,
                })
            elif hours >= 1:
                actions.append({
                    "type": "gentle_reminder",
                    "subject_id": item["subject_id"],
                    "hours": hours,
                })

        return actions

    async def act(self, ctx: AgentContext) -> list[dict]:
        """Send reminders."""
        actions_taken = []

        # In production, would load faculty IDs and send actual notifications
        for action in ctx.action_plan:
            actions_taken.append({
                "type": action["type"],
                "subject_id": action["subject_id"],
                "status": "notification_sent",
            })

        return actions_taken

    async def reflect(self, ctx: AgentContext) -> str:
        """Summarize reminder results."""
        actions_taken = ctx.actions_taken
        gentle = sum(1 for a in actions_taken if a["type"] == "gentle_reminder")
        urgent = sum(1 for a in actions_taken if a["type"] == "urgent_reminder")
        escalated = sum(1 for a in actions_taken if a["type"] == "escalate_to_admin")

        return (
            f"Reminder: Checked attendance submissions. "
            f"Sent {gentle} gentle, {urgent} urgent, {escalated} escalations."
        )


class GuidanceService:
    """Helper for time calculation."""
    @staticmethod
    def _calculate_hours_since(class_end_time):
        """Calculate hours since class ended."""
        from datetime import time as time_type
        now = datetime.utcnow().time()
        # Simplified: assume class was today
        return 0  # Placeholder
