"""Leave request service for evaluating and managing leave.

Agent 4: Leave Evaluator makes AUTO decisions based on attendance impact.
"""

import logging
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from backend.models.leave_request import LeaveRequest, LeaveStatus, LeaveDecision
from backend.models.attendance_summary import AttendanceSummary
from backend.models.subject import Subject
from backend.models.timetable import Timetable
from backend.models.student import Student
from backend.schemas.leave import (
    LeaveRequestCreate,
    LeaveRequestPreview,
    LeaveRequestResponse,
)
from backend.services.guidance_service import GuidanceService

logger = logging.getLogger(__name__)


class LeaveService:
    """Service for managing leave requests with AI evaluation."""

    @staticmethod
    async def preview_leave(
        db: AsyncSession,
        student_id: int,
        subject_id: int,
        start_date: date,
        end_date: date,
    ) -> LeaveRequestPreview:
        """Preview attendance impact of leave request.

        Args:
            db: Database session.
            student_id: Student ID.
            subject_id: Subject ID.
            start_date: Leave start date.
            end_date: Leave end date.

        Returns:
            LeaveRequestPreview with impact analysis.
        """
        try:
            # Get current summary
            summary_result = await db.execute(
                select(AttendanceSummary).filter(
                    and_(
                        AttendanceSummary.student_id == student_id,
                        AttendanceSummary.subject_id == subject_id,
                    )
                )
            )
            summary = summary_result.scalar()
            if not summary:
                return LeaveRequestPreview(
                    current_percentage=0.0,
                    new_percentage=0.0,
                    classes_missing=0,
                    classes_remaining_after=0,
                    recovery_possible=False,
                    impact_message="Subject not found in enrollment.",
                )

            # Get subject threshold
            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()
            threshold = subject.attendance_threshold

            # Count classes on leave dates (by timetable day of week)
            # This is a simplified version - in production, would query actual scheduled classes
            delta = (end_date - start_date).days + 1
            # Estimate: 3 classes per week = ~1 per 2.3 days
            estimated_classes_missing = max(0, int(delta / 2.3))

            # Get remaining classes
            remaining_result = await db.execute(
                select(func.count(Timetable.id)).filter(
                    Timetable.subject_id == subject_id,
                    Timetable.is_active == True,
                )
            )
            # Rough estimate of remaining classes
            classes_remaining = max(0, subject.total_planned_classes - summary.classes_held - estimated_classes_missing)

            # Calculate new percentage
            new_held = summary.classes_held + estimated_classes_missing
            new_attended = summary.classes_attended  # Leave doesn't affect this
            new_pct = GuidanceService.calculate_current_percentage(
                new_attended, new_held
            )

            # Check if recovery is possible
            classes_needed = GuidanceService.calculate_classes_needed_to_recover(
                new_attended, new_held, threshold
            )
            recovery_possible = classes_needed <= classes_remaining if classes_remaining > 0 else False

            # Generate impact message
            if new_pct >= threshold:
                impact_msg = f"✅ Leave approved: Attendance remains {new_pct:.1f}% (above {threshold}% threshold)"
            elif recovery_possible:
                impact_msg = f"⚠️ Attendance drops to {new_pct:.1f}%. Recovery possible if {classes_needed} classes attended."
            else:
                impact_msg = f"❌ Attendance drops to {new_pct:.1f}%. Recovery not possible before semester end."

            return LeaveRequestPreview(
                current_percentage=summary.current_percentage,
                new_percentage=round(new_pct, 1),
                classes_missing=estimated_classes_missing,
                classes_remaining_after=classes_remaining,
                recovery_possible=recovery_possible,
                impact_message=impact_msg,
            )

        except Exception as e:
            logger.error(f"Error previewing leave: {e}")
            raise

    @staticmethod
    async def evaluate_leave_request(
        db: AsyncSession,
        student_id: int,
        subject_id: int,
        start_date: date,
        end_date: date,
        reason: str,
    ) -> tuple[LeaveDecision, str, float]:
        """Agent 4: Evaluate leave request and return decision.

        Args:
            db: Database session.
            student_id: Student ID.
            subject_id: Subject ID.
            start_date: Leave start date.
            end_date: Leave end date.
            reason: Reason for leave.

        Returns:
            Tuple of (decision, reasoning, projected_percentage).
        """
        try:
            # Get preview
            preview = await LeaveService.preview_leave(
                db, student_id, subject_id, start_date, end_date
            )

            # Get summary for thresholds
            summary_result = await db.execute(
                select(AttendanceSummary).filter(
                    and_(
                        AttendanceSummary.student_id == student_id,
                        AttendanceSummary.subject_id == subject_id,
                    )
                )
            )
            summary = summary_result.scalar()
            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()
            threshold = subject.attendance_threshold

            # Decision tree (Agent 4 logic)
            if preview.new_percentage >= threshold:
                # AUTO APPROVE
                decision = LeaveDecision.AUTO_APPROVE
                reasoning = (
                    f"Leave approved automatically. Attendance remains at "
                    f"{preview.new_percentage}%, safely above {threshold}% requirement."
                )
            elif preview.new_percentage < threshold and preview.recovery_possible:
                # Check reason category
                medical_keywords = ["medical", "doctor", "hospital", "sick", "illness"]
                is_medical = any(kw in reason.lower() for kw in medical_keywords)

                if is_medical:
                    # CONDITIONAL APPROVE
                    decision = LeaveDecision.CONDITIONAL_APPROVE
                    classes_needed = GuidanceService.calculate_classes_needed_to_recover(
                        summary.classes_attended,
                        summary.classes_held + preview.classes_missing,
                        threshold,
                    )
                    reasoning = (
                        f"Leave conditionally approved (medical reason). "
                        f"Attendance drops to {preview.new_percentage}%. "
                        f"You must attend {classes_needed} consecutive classes "
                        f"after return to recover."
                    )
                else:
                    # FLAG FOR REVIEW
                    decision = LeaveDecision.FLAG_FOR_REVIEW
                    reasoning = (
                        f"Leave flagged for faculty review. Attendance would drop to "
                        f"{preview.new_percentage}% (below {threshold}% threshold). "
                        f"Recovery is possible but requires {preview.classes_remaining_after} "
                        f"consecutive attendances."
                    )
            else:
                # AUTO REJECT
                decision = LeaveDecision.AUTO_REJECT
                reasoning = (
                    f"Leave cannot be approved. Attendance would drop to "
                    f"{preview.new_percentage}%, with no possibility of recovery. "
                    f"Only {preview.classes_remaining_after} classes remain in semester."
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
        """Create leave request with automatic AI evaluation.

        Args:
            db: Database session.
            student_id: Student ID.
            leave_data: LeaveRequestCreate data.

        Returns:
            LeaveRequestResponse with AI decision.
        """
        try:
            # Evaluate leave
            decision, reasoning, new_pct = await LeaveService.evaluate_leave_request(
                db,
                student_id,
                leave_data.subject_id,
                leave_data.start_date,
                leave_data.end_date,
                leave_data.reason,
            )

            # Determine status from decision
            if decision == LeaveDecision.AUTO_APPROVE:
                status = LeaveStatus.APPROVED
            elif decision == LeaveDecision.CONDITIONAL_APPROVE:
                status = LeaveStatus.CONDITIONAL
            elif decision == LeaveDecision.FLAG_FOR_REVIEW:
                status = LeaveStatus.PENDING
            else:  # AUTO_REJECT
                status = LeaveStatus.REJECTED

            # Create request
            leave_request = LeaveRequest(
                student_id=student_id,
                subject_id=leave_data.subject_id,
                start_date=leave_data.start_date,
                end_date=leave_data.end_date,
                reason=leave_data.reason,
                attendance_impact_pct=new_pct,
                ai_decision=decision.value,
                ai_reasoning=reasoning,
                status=status,
            )
            db.add(leave_request)
            await db.commit()
            await db.refresh(leave_request)

            logger.info(
                f"Leave request created for student {student_id}: {decision.value}"
            )
            return LeaveRequestResponse.from_orm(leave_request)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating leave request: {e}")
            raise

    @staticmethod
    async def get_leave_request(
        db: AsyncSession,
        leave_request_id: int,
    ) -> LeaveRequestResponse | None:
        """Get single leave request.

        Args:
            db: Database session.
            leave_request_id: Leave request ID.

        Returns:
            LeaveRequestResponse or None.
        """
        try:
            result = await db.execute(
                select(LeaveRequest).filter(LeaveRequest.id == leave_request_id)
            )
            leave_request = result.scalar()
            if leave_request:
                return LeaveRequestResponse.from_orm(leave_request)
            return None

        except Exception as e:
            logger.error(f"Error getting leave request {leave_request_id}: {e}")
            raise
