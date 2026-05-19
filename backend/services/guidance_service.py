"""Guidance service implementing all 5 attendance calculation formulas.

Formula 1: Current Percentage = (classes_attended / classes_held) * 100
Formula 2: Zone Classification (SAFE/WARNING/DANGER/CRITICAL)
Formula 3: Classes Can Miss (when SAFE)
Formula 4: Classes Needed to Recover (when below threshold)
Formula 5: End-of-Term Projections (best/worst case)

Agent 2: Recovery Advisor generates guidance using these formulas.
"""

import logging
from math import floor, ceil
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from backend.models.attendance_summary import AttendanceSummary, AttendanceZone, AttendanceTrend
from backend.models.subject import Subject
from backend.models.student import Student
from backend.models.student_subject import StudentSubject
from backend.schemas.guidance import (
    SubjectGuidance,
    GuidanceResult,
    GuidanceMessage,
)

logger = logging.getLogger(__name__)

RMAINING_CLASSES_DEFAULT = 20


class GuidanceService:
    """Service for generating student guidance using pure math formulas."""

    @staticmethod
    def calculate_current_percentage(classes_attended: int, classes_held: int) -> float:
        """Formula 1: Calculate current attendance percentage.

        Args:
            classes_attended: Number of classes student attended.
            classes_held: Total number of classes held.

        Returns:
            Current attendance percentage (0-100).
        """
        if classes_held == 0:
            return 0.0
        return (classes_attended / classes_held) * 100

    @staticmethod
    def classify_zone(
        current_percentage: float,
        threshold: float = 75.0,
    ) -> str:
        """Formula 2: Classify student into zone based on percentage.

        Args:
            current_percentage: Current attendance percentage.
            threshold: Minimum attendance threshold (default 75%).

        Returns:
            Zone string: "safe", "warning", "danger", or "critical".
        """
        if current_percentage >= threshold:
            return AttendanceZone.SAFE
        elif current_percentage >= threshold - 10:
            return AttendanceZone.WARNING
        elif current_percentage >= threshold - 20:
            return AttendanceZone.DANGER
        else:
            return AttendanceZone.CRITICAL

    @staticmethod
    def calculate_classes_can_miss(
        classes_attended: int,
        classes_held: int,
        threshold: float = 75.0,
    ) -> int:
        """Formula 3: Calculate how many classes can be missed while staying safe.

        Only show when in SAFE zone.

        Formula:
        classes_can_miss = floor(
            (classes_attended - (threshold/100) * classes_held) / (threshold/100)
        )

        Args:
            classes_attended: Classes attended by student.
            classes_held: Total classes held.
            threshold: Attendance threshold percentage.

        Returns:
            Number of classes that can be missed (0 if already below threshold).
        """
        threshold_decimal = threshold / 100
        classes_at_threshold = threshold_decimal * classes_held

        # If already below threshold, return 0
        if classes_attended < classes_at_threshold:
            return 0

        # Calculate how many can be missed
        classes_can_miss_float = (
            classes_attended - classes_at_threshold
        ) / threshold_decimal
        return max(0, floor(classes_can_miss_float))

    @staticmethod
    def calculate_classes_needed_to_recover(
        classes_attended: int,
        classes_held: int,
        threshold: float = 75.0,
    ) -> int:
        """Formula 4: Calculate classes needed to reach threshold.

        Only show when below threshold.

        Formula:
        classes_needed = ceil(
            ((threshold/100) * classes_held - classes_attended) / (1 - threshold/100)
        )

        Args:
            classes_attended: Classes attended by student.
            classes_held: Total classes held.
            threshold: Attendance threshold percentage.

        Returns:
            Number of consecutive classes needed to reach threshold (0 if already at/above).
        """
        threshold_decimal = threshold / 100
        classes_at_threshold = threshold_decimal * classes_held

        # If already at or above threshold, return 0
        if classes_attended >= classes_at_threshold:
            return 0

        # Avoid division by zero
        denominator = 1 - threshold_decimal
        if denominator <= 0:
            return 0

        # Calculate classes needed
        classes_needed_float = (
            classes_at_threshold - classes_attended
        ) / denominator
        return max(1, ceil(classes_needed_float))

    @staticmethod
    def calculate_end_of_term_projection(
        classes_attended: int,
        classes_held: int,
        remaining_classes: int = REMAINING_CLASSES_DEFAULT,
    ) -> tuple[float, float]:
        """Formula 5: Calculate best and worst case end-of-term percentages.

        Best case: Attend all remaining classes
        Worst case: Skip all remaining classes

        Args:
            classes_attended: Classes attended so far.
            classes_held: Classes held so far.
            remaining_classes: Estimated remaining classes in semester.

        Returns:
            Tuple of (best_case_percentage, worst_case_percentage).
        """
        total_classes_if_all = classes_held + remaining_classes

        # Best case: attend all remaining
        best_pct = (
            (classes_attended + remaining_classes) / total_classes_if_all
        ) * 100

        # Worst case: skip all remaining
        worst_pct = (classes_attended / total_classes_if_all) * 100

        return round(best_pct, 1), round(worst_pct, 1)

    @staticmethod
    def generate_guidance_message(
        zone: str,
        student_name: str,
        subject_name: str,
        current_percentage: float,
        threshold: float,
        classes_can_miss: int = 0,
        classes_needed: int = 0,
    ) -> GuidanceMessage:
        """Generate template-based guidance message (pure strings, no LLM).

        Args:
            zone: Current zone (safe/warning/danger/critical).
            student_name: Student's name.
            subject_name: Subject name.
            current_percentage: Current attendance percentage.
            threshold: Attendance threshold.
            classes_can_miss: (For SAFE zone) Classes that can be missed.
            classes_needed: (For below threshold) Classes needed to recover.

        Returns:
            GuidanceMessage with message and action.
        """
        pct_str = f"{current_percentage:.1f}"
        threshold_str = f"{threshold:.0f}"

        if zone == AttendanceZone.SAFE:
            message = (
                f"Great work {student_name}! Your {subject_name} attendance is "
                f"{pct_str}%, well above the {threshold_str}% requirement. "
                f"You can miss up to {classes_can_miss} more class(es) and still stay safe. "
                f"Keep it up!"
            )
            action = "Keep attending regularly to maintain your standing."

        elif zone == AttendanceZone.WARNING:
            message = (
                f"Heads up {student_name}! Your {subject_name} attendance is "
                f"{pct_str}%, getting close to the {threshold_str}% limit. "
                f"You can only miss {classes_can_miss} more class(es). "
                f"Try not to skip any upcoming lectures."
            )
            action = "Avoid missing any classes this week."

        elif zone == AttendanceZone.DANGER:
            message = (
                f"Attention {student_name}! Your {subject_name} attendance has dropped to "
                f"{pct_str}%, below the required {threshold_str}%. "
                f"You must attend the next {classes_needed} consecutive class(es) to recover. "
                f"Please prioritize this subject."
            )
            action = "Attend all upcoming classes. Speak with your faculty."

        else:  # CRITICAL
            message = (
                f"URGENT {student_name}! Your {subject_name} attendance is critically "
                f"low at {pct_str}%. You need {classes_needed} more classes just to reach "
                f"the minimum {threshold_str}% requirement."
            )
            action = "Meet your faculty immediately and attend every single class."

        return GuidanceMessage(
            zone=zone,
            student_name=student_name,
            subject_name=subject_name,
            current_percentage=current_percentage,
            threshold=threshold,
            can_miss=classes_can_miss,
            classes_needed=classes_needed,
            message=message,
            action=action,
        )

    @staticmethod
    def detect_trend(
        recent_percentages: list[float],
    ) -> str:
        """Detect attendance trend (improving/declining/stable).

        Args:
            recent_percentages: List of recent percentages (oldest to newest).

        Returns:
            Trend: "improving", "declining", or "stable".
        """
        if len(recent_percentages) < 2:
            return AttendanceTrend.STABLE

        # Compare trend across last 5 records
        if len(recent_percentages) >= 5:
            old_avg = sum(recent_percentages[:2]) / 2
            new_avg = sum(recent_percentages[-2:]) / 2
        else:
            old_avg = recent_percentages[0]
            new_avg = recent_percentages[-1]

        diff = new_avg - old_avg

        if diff > 2:  # Improved by more than 2%
            return AttendanceTrend.IMPROVING
        elif diff < -2:  # Declined by more than 2%
            return AttendanceTrend.DECLINING
        else:
            return AttendanceTrend.STABLE

    @staticmethod
    def calculate_health_score(subject_summaries: list[AttendanceSummary]) -> float:
        """Calculate overall health score (0-100).

        Weighted by threshold gap: subjects closer to threshold are weighted higher.

        Args:
            subject_summaries: List of AttendanceSummary for student's subjects.

        Returns:
            Overall health score 0-100.
        """
        if not subject_summaries:
            return 0.0

        total_weight = 0.0
        weighted_sum = 0.0

        for summary in subject_summaries:
            # Get subject threshold (assume 75.0 if not available)
            threshold = 75.0

            # Weight by gap from threshold
            gap = abs(summary.current_percentage - threshold)
            weight = 1 + (gap / 100)  # Closer to threshold = higher weight

            weighted_sum += summary.current_percentage * weight
            total_weight += weight

        if total_weight == 0:
            return 0.0

        score = weighted_sum / total_weight
        return round(min(100.0, max(0.0, score)), 1)

    async def get_student_guidance(
        self,
        db: AsyncSession,
        student_id: int,
    ) -> GuidanceResult:
        """Generate complete guidance for student (Agent 2 implementation).

        Args:
            db: Database session.
            student_id: ID of student.

        Returns:
            GuidanceResult with health score, subjects by priority, and messages.
        """
        try:
            # Load student's enrolled subjects
            student_subjects_result = await db.execute(
                select(StudentSubject).filter(
                    StudentSubject.student_id == student_id
                )
            )
            student_subjects = student_subjects_result.scalars().all()

            if not student_subjects:
                return GuidanceResult(
                    overall_health_score=0.0,
                    subjects_by_priority=[],
                    top_priority_message="No subjects enrolled.",
                    safe_subjects_count=0,
                    at_risk_subjects_count=0,
                    generated_at=datetime.utcnow(),
                )

            # Load summaries and subjects
            subject_ids = [ss.subject_id for ss in student_subjects]
            summaries_result = await db.execute(
                select(AttendanceSummary).filter(
                    and_(
                        AttendanceSummary.student_id == student_id,
                        AttendanceSummary.subject_id.in_(subject_ids),
                    )
                )
            )
            summaries = summaries_result.scalars().all()

            subjects_result = await db.execute(
                select(Subject).filter(Subject.id.in_(subject_ids))
            )
            subjects_by_id = {s.id: s for s in subjects_result.scalars().all()}

            # Load student name
            student_result = await db.execute(
                select(Student).filter(Student.id == student_id)
            )
            student = student_result.scalar_one()
            student_name = student.user.full_name if student.user else "Student"

            # Build subject guidance list
            subject_guidances: list[SubjectGuidance] = []
            safe_count = 0
            at_risk_count = 0

            for summary in summaries:
                subject = subjects_by_id.get(summary.subject_id)
                if not subject:
                    continue

                threshold = subject.attendance_threshold

                # Calculate classes can miss / needed
                classes_can_miss = self.calculate_classes_can_miss(
                    summary.classes_attended,
                    summary.classes_held,
                    threshold,
                )
                classes_needed = self.calculate_classes_needed_to_recover(
                    summary.classes_attended,
                    summary.classes_held,
                    threshold,
                )

                # Project end of term
                best_case, worst_case = self.calculate_end_of_term_projection(
                    summary.classes_attended,
                    summary.classes_held,
                )

                # Generate message
                msg = self.generate_guidance_message(
                    zone=summary.zone,
                    student_name=student_name,
                    subject_name=subject.name,
                    current_percentage=summary.current_percentage,
                    threshold=threshold,
                    classes_can_miss=classes_can_miss,
                    classes_needed=classes_needed,
                )

                # Determine urgency rank (1=critical, 4=safe)
                if summary.zone == AttendanceZone.CRITICAL:
                    urgency_rank = 1
                    at_risk_count += 1
                elif summary.zone == AttendanceZone.DANGER:
                    urgency_rank = 2
                    at_risk_count += 1
                elif summary.zone == AttendanceZone.WARNING:
                    urgency_rank = 3
                    at_risk_count += 1
                else:  # SAFE
                    urgency_rank = 4
                    safe_count += 1

                subject_guidance = SubjectGuidance(
                    subject_id=subject.id,
                    subject_name=subject.name,
                    zone=summary.zone,
                    current_percentage=summary.current_percentage,
                    threshold=threshold,
                    classes_held=summary.classes_held,
                    classes_attended=summary.classes_attended,
                    classes_can_miss=classes_can_miss,
                    classes_needed=classes_needed,
                    projected_best=best_case,
                    projected_worst=worst_case,
                    message=msg.message,
                    action=msg.action,
                    urgency_rank=urgency_rank,
                    trend=summary.trend,
                )
                subject_guidances.append(subject_guidance)

            # Sort by urgency (critical first, then danger, warning, safe)
            subject_guidances.sort(key=lambda x: x.urgency_rank)

            # Calculate overall health score
            overall_health = self.calculate_health_score(summaries)

            # Determine top priority message
            if subject_guidances:
                top_priority = subject_guidances[0]
                if top_priority.urgency_rank <= 2:  # Critical or Danger
                    top_priority_message = (
                        f"⚠️ PRIORITY: {top_priority.subject_name} requires immediate action. "
                        f"{top_priority.action}"
                    )
                elif top_priority.urgency_rank == 3:  # Warning
                    top_priority_message = (
                        f"📌 ATTENTION: {top_priority.subject_name} is at risk. "
                        f"{top_priority.action}"
                    )
                else:  # Safe
                    top_priority_message = "✅ All subjects are in safe zone. Keep up the good work!"
            else:
                top_priority_message = "No subjects enrolled."

            return GuidanceResult(
                overall_health_score=overall_health,
                subjects_by_priority=subject_guidances,
                top_priority_message=top_priority_message,
                safe_subjects_count=safe_count,
                at_risk_subjects_count=at_risk_count,
                generated_at=datetime.utcnow(),
            )

        except Exception as e:
            logger.error(f"Error generating guidance for student {student_id}: {e}")
            raise
