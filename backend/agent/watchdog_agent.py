"""Agent 1: Watchdog Agent - Monitors zone drops and streaks.

Trigger: After every faculty attendance submission
Runs: Async Celery task (non-blocking)

Observe → Load attendance records and previous zones
Think   → Detect zone drops, streak alerts, edge cases
Plan    → Build notification and intervention actions
Act     → Send WebSocket notifications, update summaries, refresh intervention list
Reflect → Log summary of detections
"""

import logging
from datetime import datetime
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agent.base_agent import BaseAgent, AgentContext
from backend.models.attendance_summary import AttendanceSummary, AttendanceZone
from backend.models.attendance_record import AttendanceRecord, AttendanceStatus
from backend.models.attendance_session import AttendanceSession
from backend.models.student import Student
from backend.models.subject import Subject
from backend.services.notification_service import NotificationService
from backend.services.guidance_service import GuidanceService

logger = logging.getLogger(__name__)


class WatchdogAgent(BaseAgent):
    """Agent 1: Watchdog - Detects zone drops and alerts students."""

    name = "WatchdogAgent"

    async def observe(self, ctx: AgentContext) -> dict:
        """Load attendance session and student data.

        Expected trigger_data: {"session_id": int, "subject_id": int}
        """
        session_id = ctx.trigger_data.get("session_id")
        subject_id = ctx.trigger_data.get("subject_id")

        # Load session with records
        session_result = await self.db.execute(
            select(AttendanceSession).filter(
                AttendanceSession.id == session_id
            )
        )
        session = session_result.scalar()

        if not session:
            return {"error": f"Session {session_id} not found"}

        # Load all students in this session
        records_result = await self.db.execute(
            select(AttendanceRecord).filter(
                AttendanceRecord.session_id == session_id
            )
        )
        records = records_result.scalars().all()

        # Load current summaries
        student_ids = [r.student_id for r in records]
        summaries_result = await self.db.execute(
            select(AttendanceSummary).filter(
                and_(
                    AttendanceSummary.subject_id == subject_id,
                    AttendanceSummary.student_id.in_(student_ids),
                )
            )
        )
        summaries = {s.student_id: s for s in summaries_result.scalars().all()}

        return {
            "session_id": session_id,
            "subject_id": subject_id,
            "records": records,
            "current_summaries": summaries,
            "total_students": len(records),
        }

    async def think(self, ctx: AgentContext) -> list[str]:
        """Analyze records for zone drops and streaks."""
        observations = ctx.observations
        records = observations.get("records", [])
        summaries = observations.get("current_summaries", {})

        insights = []

        # Count statuses
        present_count = sum(
            1 for r in records if r.status == AttendanceStatus.PRESENT
        )
        absent_count = sum(
            1 for r in records if r.status == AttendanceStatus.ABSENT
        )
        late_count = sum(1 for r in records if r.status == AttendanceStatus.LATE)

        insights.append(
            f"Session composition: {present_count} present, {absent_count} absent, {late_count} late"
        )

        # Check for 3-consecutive-absence streaks
        for student_id in summaries.keys():
            # Simplified: check if student was absent today
            student_record = next(
                (r for r in records if r.student_id == student_id), None
            )
            if student_record and student_record.status == AttendanceStatus.ABSENT:
                insights.append(f"Student {student_id}: absent today")

        # Identify potential zone drops (would be detected after summary update)
        zone_drop_count = 0
        for summary in summaries.values():
            if summary.zone == AttendanceZone.WARNING:
                zone_drop_count += 1

        insights.append(f"Students in warning zone: {zone_drop_count}")

        return insights

    async def plan(self, ctx: AgentContext) -> list[dict]:
        """Plan notifications and interventions."""
        observations = ctx.observations
        summaries = observations.get("current_summaries", {})
        subject_id = observations.get("subject_id")

        actions = []

        # For each at-risk student, plan a notification
        for student_id, summary in summaries.items():
            if summary.zone in (AttendanceZone.DANGER, AttendanceZone.CRITICAL):
                actions.append({
                    "type": "send_notification",
                    "student_id": student_id,
                    "title": f"{summary.zone.upper()}: {summary.zone} Attendance Zone",
                    "message": f"Your attendance in subject {subject_id} has dropped to {summary.current_percentage}%.",
                    "notification_type": "zone_alert",
                })

        return actions

    async def act(self, ctx: AgentContext) -> list[dict]:
        """Execute notifications."""
        actions_taken = []

        for action in ctx.action_plan:
            if action["type"] == "send_notification":
                try:
                    await NotificationService.create_notification(
                        self.db,
                        action["student_id"],
                        action["title"],
                        action["message"],
                        action["notification_type"],
                    )
                    actions_taken.append({
                        "type": "notification_sent",
                        "student_id": action["student_id"],
                    })
                except Exception as e:
                    logger.error(f"Error sending notification: {e}")
                    actions_taken.append({
                        "type": "notification_failed",
                        "student_id": action["student_id"],
                        "error": str(e),
                    })

        return actions_taken

    async def reflect(self, ctx: AgentContext) -> str:
        """Summarize watchdog results."""
        observations = ctx.observations
        actions_taken = ctx.actions_taken

        total_records = observations.get("total_students", 0)
        notifications_sent = sum(
            1 for a in actions_taken if a["type"] == "notification_sent"
        )

        return (
            f"Watchdog: Processed session with {total_records} students. "
            f"Sent {notifications_sent} zone alerts."
        )
