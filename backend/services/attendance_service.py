"""Attendance service for recording and managing attendance records.

CRITICAL RULE:
  Every INSERT/UPDATE to attendance_records MUST call update_attendance_summary().
  This keeps the denormalized cache synchronized.
"""

import logging
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from backend.models.attendance_record import AttendanceRecord, AttendanceStatus
from backend.models.attendance_session import AttendanceSession
from backend.models.attendance_summary import AttendanceSummary, AttendanceZone
from backend.models.student import Student
from backend.models.subject import Subject
from backend.models.student_subject import StudentSubject
from backend.schemas.attendance import (
    AttendanceSessionCreate,
    AttendanceSessionResponse,
    AttendanceSessionPreview,
    AttendanceSummaryResponse,
    StudentAttendanceDetail,
    StudentFullAttendance,
)
from backend.services.guidance_service import GuidanceService

logger = logging.getLogger(__name__)


class AttendanceService:
    """Service for managing attendance records and summaries."""

    @staticmethod
    async def preview_attendance(
        db: AsyncSession,
        subject_id: int,
        attendance_records: list[dict],
    ) -> AttendanceSessionPreview:
        """Preview attendance changes before submission.

        Shows which students will experience zone drops after recording.

        Args:
            db: Database session.
            subject_id: Subject ID.
            attendance_records: List of {student_id, status} dicts.

        Returns:
            AttendanceSessionPreview with impact analysis.
        """
        try:
            # Load subject and threshold
            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()
            threshold = subject.attendance_threshold

            # Load current summaries for all students
            student_ids = [r["student_id"] for r in attendance_records]
            summaries_result = await db.execute(
                select(AttendanceSummary).filter(
                    and_(
                        AttendanceSummary.subject_id == subject_id,
                        AttendanceSummary.student_id.in_(student_ids),
                    )
                )
            )
            current_summaries = {s.student_id: s for s in summaries_result.scalars().all()}

            # Count statuses
            present_count = sum(1 for r in attendance_records if r["status"] == AttendanceStatus.PRESENT)
            absent_count = sum(1 for r in attendance_records if r["status"] == AttendanceStatus.ABSENT)
            late_count = sum(1 for r in attendance_records if r["status"] == AttendanceStatus.LATE)

            # Detect zone drops
            zone_drops = []
            students_at_risk = 0

            for record in attendance_records:
                student_id = record["student_id"]
                status = record["status"]

                current_summary = current_summaries.get(student_id)
                if not current_summary:
                    continue

                # Calculate new percentage after this record
                new_attended = current_summary.classes_attended
                if status == AttendanceStatus.PRESENT:
                    new_attended += 1
                # late counts as attended
                elif status == AttendanceStatus.LATE:
                    new_attended += 1
                # absent doesn't increment

                new_held = current_summary.classes_held + 1
                new_pct = GuidanceService.calculate_current_percentage(
                    new_attended, new_held
                )
                new_zone = GuidanceService.classify_zone(new_pct, threshold)

                # Check if zone drops
                old_zone = current_summary.zone
                if AttendanceService._zone_priority(new_zone) < AttendanceService._zone_priority(old_zone):
                    # Zone dropped
                    student_result = await db.execute(
                        select(Student).filter(Student.id == student_id)
                    )
                    student = student_result.scalar_one()
                    zone_drops.append({
                        "student_id": student_id,
                        "student_name": student.user.full_name if student.user else "Unknown",
                        "old_percentage": round(current_summary.current_percentage, 1),
                        "new_percentage": round(new_pct, 1),
                        "old_zone": old_zone,
                        "new_zone": new_zone,
                    })

                # Count at-risk students (in danger or critical after update)
                if new_zone in (AttendanceZone.DANGER, AttendanceZone.CRITICAL):
                    students_at_risk += 1

            return AttendanceSessionPreview(
                total_students=len(attendance_records),
                present_count=present_count,
                absent_count=absent_count,
                late_count=late_count,
                zone_drops=zone_drops,
                students_at_risk=students_at_risk,
            )

        except Exception as e:
            logger.error(f"Error previewing attendance: {e}")
            raise

    @staticmethod
    def _zone_priority(zone: str) -> int:
        """Get priority level of zone (lower = more urgent).

        Args:
            zone: Zone string.

        Returns:
            Priority number (1=critical, 4=safe).
        """
        priority_map = {
            AttendanceZone.CRITICAL: 1,
            AttendanceZone.DANGER: 2,
            AttendanceZone.WARNING: 3,
            AttendanceZone.SAFE: 4,
        }
        return priority_map.get(zone, 5)

    @staticmethod
    async def create_attendance_session(
        db: AsyncSession,
        faculty_id: int,
        session_data: AttendanceSessionCreate,
    ) -> AttendanceSessionResponse:
        """Create attendance session and records.

        CRITICAL: Calls update_attendance_summary() after all records inserted.

        Args:
            db: Database session.
            faculty_id: Faculty ID submitting attendance.
            session_data: Session creation data with records.

        Returns:
            AttendanceSessionResponse.
        """
        try:
            # Create session
            session = AttendanceSession(
                subject_id=session_data.subject_id,
                faculty_id=faculty_id,
                date=session_data.date,
                notes=session_data.notes,
                submitted_at=datetime.utcnow(),
            )
            db.add(session)
            await db.flush()  # Get session ID without committing

            # Create records
            records = []
            for record_data in session_data.records:
                record = AttendanceRecord(
                    session_id=session.id,
                    student_id=record_data.student_id,
                    status=record_data.status,
                    marked_by_id=faculty_id,
                    created_at=datetime.utcnow(),
                )
                db.add(record)
                records.append(record)

            await db.flush()

            # CRITICAL: Update attendance summary for all affected students
            await AttendanceService.update_attendance_summary(
                db,
                session.subject_id,
                [r.student_id for r in records],
            )

            await db.commit()

            # Reload session with records
            await db.refresh(session)
            return AttendanceSessionResponse.from_orm(session)

        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating attendance session: {e}")
            raise

    @staticmethod
    async def update_attendance_summary(
        db: AsyncSession,
        subject_id: int,
        student_ids: list[int] | None = None,
    ) -> None:
        """Update denormalized attendance_summary for students in a subject.

        This is THE CRITICAL METHOD that keeps cache synchronized.
        Call after EVERY attendance_record insert/update/delete.

        Args:
            db: Database session.
            subject_id: Subject ID.
            student_ids: Specific student IDs to update (None = all enrolled).
        """
        try:
            # Get all enrolled students if not specified
            if student_ids is None:
                student_subjects_result = await db.execute(
                    select(StudentSubject).filter(
                        StudentSubject.subject_id == subject_id
                    )
                )
                student_ids = [
                    ss.student_id
                    for ss in student_subjects_result.scalars().all()
                ]

            if not student_ids:
                return

            # Load subject for threshold
            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()
            threshold = subject.attendance_threshold

            # Process each student
            for student_id in student_ids:
                # Count classes held
                sessions_result = await db.execute(
                    select(func.count(AttendanceSession.id)).filter(
                        AttendanceSession.subject_id == subject_id
                    )
                )
                classes_held = sessions_result.scalar() or 0

                # Count classes attended (present or late)
                attended_result = await db.execute(
                    select(func.count(AttendanceRecord.id)).filter(
                        and_(
                            AttendanceRecord.student_id == student_id,
                            AttendanceRecord.session_id.in_(
                                select(AttendanceSession.id).filter(
                                    AttendanceSession.subject_id == subject_id
                                )
                            ),
                            AttendanceRecord.status.in_(
                                [AttendanceStatus.PRESENT, AttendanceStatus.LATE]
                            ),
                        )
                    )
                )
                classes_attended = attended_result.scalar() or 0

                # Calculate percentage and zone
                current_pct = GuidanceService.calculate_current_percentage(
                    classes_attended, classes_held
                )
                zone = GuidanceService.classify_zone(current_pct, threshold)

                # Calculate classes can miss / needed
                classes_can_miss = GuidanceService.calculate_classes_can_miss(
                    classes_attended, classes_held, threshold
                )
                classes_needed = GuidanceService.calculate_classes_needed_to_recover(
                    classes_attended, classes_held, threshold
                )

                # Get or create summary
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
                    # Create new summary
                    summary = AttendanceSummary(
                        student_id=student_id,
                        subject_id=subject_id,
                        classes_held=classes_held,
                        classes_attended=classes_attended,
                        current_percentage=current_pct,
                        zone=zone,
                        classes_can_miss=classes_can_miss,
                        classes_needed=classes_needed,
                    )
                    db.add(summary)
                else:
                    # Update existing summary
                    summary.classes_held = classes_held
                    summary.classes_attended = classes_attended
                    summary.current_percentage = round(current_pct, 1)
                    summary.zone = zone
                    summary.classes_can_miss = classes_can_miss
                    summary.classes_needed = classes_needed
                    summary.last_updated = datetime.utcnow()

            await db.commit()
            logger.info(
                f"Updated attendance summary for {len(student_ids)} students "
                f"in subject {subject_id}"
            )

        except Exception as e:
            await db.rollback()
            logger.error(f"Error updating attendance summary: {e}")
            raise

    @staticmethod
    async def get_student_attendance_detail(
        db: AsyncSession,
        student_id: int,
        subject_id: int,
    ) -> StudentAttendanceDetail | None:
        """Get attendance details for student in one subject.

        Args:
            db: Database session.
            student_id: Student ID.
            subject_id: Subject ID.

        Returns:
            StudentAttendanceDetail or None if not found.
        """
        try:
            # Get summary
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
                return None

            # Get subject
            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()

            # Calculate projections
            best_case, worst_case = GuidanceService.calculate_end_of_term_projection(
                summary.classes_attended,
                summary.classes_held,
            )

            return StudentAttendanceDetail(
                subject_id=subject.id,
                subject_name=subject.name,
                current_percentage=summary.current_percentage,
                zone=summary.zone,
                classes_held=summary.classes_held,
                classes_attended=summary.classes_attended,
                classes_can_miss=summary.classes_can_miss,
                classes_needed=summary.classes_needed,
                best_case_percentage=best_case,
                worst_case_percentage=worst_case,
                trend=summary.trend,
                threshold=subject.attendance_threshold,
            )

        except Exception as e:
            logger.error(
                f"Error getting attendance detail for student {student_id} "
                f"subject {subject_id}: {e}"
            )
            raise

    @staticmethod
    async def get_student_full_attendance(
        db: AsyncSession,
        student_id: int,
    ) -> StudentFullAttendance | None:
        """Get student's full attendance across all enrolled subjects.

        Args:
            db: Database session.
            student_id: Student ID.

        Returns:
            StudentFullAttendance or None if student not found.
        """
        try:
            # Load student
            student_result = await db.execute(
                select(Student).filter(Student.id == student_id)
            )
            student = student_result.scalar()
            if not student:
                return None

            # Load all summaries for student
            summaries_result = await db.execute(
                select(AttendanceSummary).filter(
                    AttendanceSummary.student_id == student_id
                )
            )
            summaries = summaries_result.scalars().all()

            # Convert to StudentAttendanceDetail
            details: list[StudentAttendanceDetail] = []
            for summary in summaries:
                detail = await AttendanceService.get_student_attendance_detail(
                    db, student_id, summary.subject_id
                )
                if detail:
                    details.append(detail)

            # Calculate health score
            guidance_service = GuidanceService()
            health_score = guidance_service.calculate_health_score(summaries)

            return StudentFullAttendance(
                student_id=student.id,
                full_name=student.user.full_name if student.user else "Unknown",
                roll_number=student.roll_number,
                semester=student.semester,
                subjects=details,
                overall_health_score=health_score,
            )

        except Exception as e:
            logger.error(f"Error getting full attendance for student {student_id}: {e}")
            raise
