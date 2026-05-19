"""Leave request service for student absence management.

Agent 4: Leave Evaluator is integrated here.
"""

import logging
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func as sql_func

from backend.models.leave_request import LeaveRequest, LeaveStatus, LeaveDecision
from backend.models.attendance_summary import AttendanceSummary
from backend.models.subject import Subject
from backend.models.timetable import Timetable
from backend.schemas.leave import (
    LeaveRequestCreate,
    LeaveRequestPreview,
    LeaveRequestResponse,
)
from backend.services.guidance_service import GuidanceService

logger = logging.getLogger(__name__)


class LeaveService:
    """Service for managing leave requests with Agent 4 evaluation."""

    @staticmethod
    async def preview_leave_impact(
        db: AsyncSession,
        student_id: int,
        subject_id: int,
        start_date: date,
        end_date: date,
    ) -> LeaveRequestPreview:
        """Preview leave request impact before submission (Agent 4 OBSERVE).

        Args:
            db: Database session.
            student_id: Student ID.
            subject_id: Subject ID.
            start_date: Leave start date.
            end_date: Leave end date.

        Returns:
            LeaveRequestPreview showing impact.
        """
        try:
            # Load current summary
            summary_result = await db.execute(
                select(AttendanceSummary).filter(
                    and_(
                        AttendanceSummary.student_id == student_id,
                        AttendanceSummary.subject_id == subject_id,
                    )
                )
            )
            summary = summary_result.scalar_one()

            # Load subject for threshold
            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()
            threshold = subject.attendance_threshold

            # Count classes on leave dates
            timetable_result = await db.execute(
                select(Timetable).filter(
                    Timetable.subject_id == subject_id
                )
            )
            timetables = timetable_result.scalars().all()

            # Simple day-of-week matching (can be enhanced)
            day_map = {
                "Monday": 0,
                "Tuesday": 1,
                "Wednesday": 2,
                "Thursday": 3,
                "Friday": 4,
                "Saturday": 5,
                "Sunday": 6,
            }

            classes_missing = 0
            current_date = start_date
            while current_date <= end_date:
                day_name = current_date.strftime("%A")
                if any(t.day_of_week == day_name for t in timetables):
                    classes_missing += 1
                current_date = current_date + __import__("datetime").timedelta(days=1)

            # Calculate new percentage
            new_held = summary.classes_held + classes_missing
            new_pct = GuidanceService.calculate_current_percentage(
                summary.classes_attended,
                new_held,
            )

            # Calculate recovery possibility
            remaining_after_leave = subject.total_planned_classes - new_held
            classes_needed = GuidanceService.calculate_classes_needed_to_recover(
                summary.classes_attended,
                new_held,
                threshold,
            )
            recovery_possible = classes_needed <= remaining_after_leave

            # Generate impact message
            if new_pct >= threshold:
                impact_message = (
                    f"Approved: Attendance remains at {new_pct:.1f}% "
                    f"(above {threshold:.0f}% threshold)."
                )
            elif recovery_possible:
                impact_message = (
                    f"Attendance will drop to {new_pct:.1f}% "
                    f"(below threshold). Recovery possible with {classes_needed} "
                    f"consecutive classes."
                )
            else:
                impact_message = (
                    f"Attendance will drop to {new_pct:.1f}% with no recovery "
                    f"possibility before semester ends."
                )

            return LeaveRequestPreview(
                current_percentage=summary.current_percentage,
                new_percentage=round(new_pct, 1),
                classes_missing=classes_missing,
                classes_remaining_after=remaining_after_leave,
                recovery_possible=recovery_possible,
                impact_message=impact_message,
            )

        except Exception as e:
            logger.error(f"Error previewing leave impact: {e}")
            raise

    @staticmethod
    async def evaluate_leave_request(
        db: AsyncSession,
        student_id: int,
        subject_id: int,
        start_date: date,
        end_date: date,
        reason: str,
    ) -> tuple[str, str, float]:
        """Agent 4: Evaluate leave request and return decision.

        Decision tree:
        - AUTO_APPROVE if new_pct >= threshold
        - CONDITIONAL_APPROVE if below threshold but recovery possible + medical
        - FLAG_FOR_REVIEW if below threshold but recovery possible + other reason
        - AUTO_REJECT if not recovery possible

        Args:
            db: Database session.
            student_id: Student ID.
            subject_id: Subject ID.
            start_date: Leave start date.
            end_date: Leave end date.
            reason: Reason for leave.

        Returns:
            Tuple of (decision, reasoning, new_percentage).
        """
        try:
            preview = await LeaveService.preview_leave_impact(
                db, student_id, subject_id, start_date, end_date
            )

            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()
            threshold = subject.attendance_threshold

            # Determine leave reason category
            medical_keywords = ["medical", "doctor", "hospital", "illness", "sick"]
            is_medical = any(
                keyword in reason.lower() for keyword in medical_keywords
            )

            # Decision logic
            if preview.new_percentage >= threshold:
                decision = LeaveDecision.AUTO_APPROVE
                reasoning = (
                    f"Attendance remains at {preview.new_percentage:.1f}% "
                    f"(above {threshold:.0f}% threshold). Approved automatically."
                )
            elif not preview.recovery_possible:
                decision = LeaveDecision.AUTO_REJECT
                reasoning = (
                    f"Attendance will drop to {preview.new_percentage:.1f}% with no "
                    f"recovery possibility. Rejected."
                )
            elif is_medical:
                decision = LeaveDecision.CONDITIONAL_APPROVE
                reasoning = (
                    f"Medical leave: Attendance will drop to {preview.new_percentage:.1f}%. "
                    f"Recovery possible with {preview.classes_remaining_after} classes. "
                    f"Approved with note to attend all upcoming classes."
                )
            else:
                decision = LeaveDecision.FLAG_FOR_REVIEW
                reasoning = (
                    f"Attendance will drop to {preview.new_percentage:.1f}%. "
                    f"Recovery possible but personal reason. Flagged for faculty review."
                )

            return decision, reasoning, preview.new_percentage

        except Exception as e:
            logger.error(f"Error evaluating leave request: {e}")
            raise

    @staticmethod
    async def create_leave_request(
        db: AsyncSession,
        student_id: int,
        leave_data: LeaveRequestCreate,
    ) -> LeaveRequestResponse:
        """Create leave request with automatic Agent 4 evaluation.

        Args:
            db: Database session.
            student_id: Student ID.
            leave_data: Leave request creation data.

        Returns:
            LeaveRequestResponse with AI decision.
        """
        try:
            # Evaluate using Agent 4
            decision, reasoning, new_pct = await LeaveService.evaluate_leave_request(
                db,
                student_id,
                leave_data.subject_id,
                leave_data.start_date,
                leave_data.end_date,
                leave_data.reason,
            )

            # Map decision to status
            status_map = {
                LeaveDecision.AUTO_APPROVE: LeaveStatus.APPROVED,
                LeaveDecision.CONDITIONAL_APPROVE: LeaveStatus.CONDITIONAL,
                LeaveDecision.FLAG_FOR_REVIEW: LeaveStatus.PENDING,
                LeaveDecision.AUTO_REJECT: LeaveStatus.REJECTED,
            }

            # Create leave request
            leave_request = LeaveRequest(
                student_id=student_id,
                subject_id=leave_data.subject_id,
                start_date=leave_data.start_date,
                end_date=leave_data.end_date,
                reason=leave_data.reason,
                ai_decision=decision,
                ai_reasoning=reasoning,
                status=status_map[decision],
                attendance_impact_pct=new_pct,
                created_at=datetime.utcnow(),
            )
            db.add(leave_request)
            await db.commit()
            await db.refresh(leave_request)

            logger.info(
                f"Created leave request {leave_request.id} for student {student_id}: "
                f"decision={decision}"
            )
            return LeaveRequestResponse.from_orm(leave_request)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating leave request: {e}")
            raise

    @staticmethod
    async def get_student_leave_history(
        db: AsyncSession,
        student_id: int,
    ) -> list[LeaveRequestResponse]:
        """Get student's leave request history.

        Args:
            db: Database session.
            student_id: Student ID.

        Returns:
            List of LeaveRequestResponse.
        """
        try:
            result = await db.execute(
                select(LeaveRequest)
                .filter(LeaveRequest.student_id == student_id)
                .order_by(LeaveRequest.created_at.desc())
            )
            requests = result.scalars().all()

            return [
                LeaveRequestResponse.from_orm(r) for r in requests
            ]

        except Exception as e:
            logger.error(f"Error getting leave history for student {student_id}: {e}")
            raise
