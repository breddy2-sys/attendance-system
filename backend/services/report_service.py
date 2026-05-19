"""Report generation service for PDF and CSV exports."""

import logging
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from backend.models.attendance_summary import AttendanceSummary
from backend.models.attendance_session import AttendanceSession
from backend.models.subject import Subject
from backend.models.student import Student
from backend.models.department import Department
from backend.schemas.report import (
    SubjectReportRow,
    SubjectAttendanceReport,
    DepartmentReportSummary,
    WeeklyReportSummary,
)

logger = logging.getLogger(__name__)


class ReportService:
    """Service for generating attendance reports."""

    @staticmethod
    async def generate_subject_report(
        db: AsyncSession,
        subject_id: int,
    ) -> SubjectAttendanceReport:
        """Generate attendance report for a subject.

        Args:
            db: Database session.
            subject_id: Subject ID.

        Returns:
            SubjectAttendanceReport with all enrolled students.
        """
        try:
            # Load subject
            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()

            # Load all summaries for subject
            summaries_result = await db.execute(
                select(AttendanceSummary).filter(
                    AttendanceSummary.subject_id == subject_id
                )
            )
            summaries = summaries_result.scalars().all()

            # Load students
            student_ids = [s.student_id for s in summaries]
            students_result = await db.execute(
                select(Student).filter(Student.id.in_(student_ids))
            )
            students_by_id = {s.id: s for s in students_result.scalars().all()}

            # Build report rows
            rows = []
            zone_distribution = {"safe": 0, "warning": 0, "danger": 0, "critical": 0}
            total_pct = 0.0

            for summary in summaries:
                student = students_by_id.get(summary.student_id)
                if not student:
                    continue

                rows.append(
                    SubjectReportRow(
                        student_id=student.id,
                        full_name=student.user.full_name if student.user else "Unknown",
                        roll_number=student.roll_number,
                        classes_attended=summary.classes_attended,
                        classes_held=summary.classes_held,
                        percentage=summary.current_percentage,
                        zone=summary.zone,
                    )
                )

                zone_distribution[summary.zone] += 1
                total_pct += summary.current_percentage

            avg_pct = total_pct / len(rows) if rows else 0.0

            return SubjectAttendanceReport(
                subject_id=subject.id,
                subject_name=subject.name,
                faculty_name=(
                    subject.faculty.user.full_name
                    if subject.faculty and subject.faculty.user
                    else "Unassigned"
                ),
                total_students=len(rows),
                average_percentage=round(avg_pct, 1),
                students_by_zone=zone_distribution,
                rows=rows,
            )

        except Exception as e:
            logger.error(f"Error generating subject report: {e}")
            raise

    @staticmethod
    async def generate_department_report(
        db: AsyncSession,
        department_id: int,
    ) -> DepartmentReportSummary:
        """Generate report for entire department.

        Args:
            db: Database session.
            department_id: Department ID.

        Returns:
            DepartmentReportSummary with all subjects.
        """
        try:
            # Load department
            dept_result = await db.execute(
                select(Department).filter(Department.id == department_id)
            )
            department = dept_result.scalar_one()

            # Load all subjects in department
            subjects_result = await db.execute(
                select(Subject).filter(Subject.department_id == department_id)
            )
            subjects = subjects_result.scalars().all()

            # Generate report for each subject
            subject_reports = []
            total_pct = 0.0
            total_students = 0
            zone_distribution = {"safe": 0, "warning": 0, "danger": 0, "critical": 0}

            for subject in subjects:
                report = await ReportService.generate_subject_report(
                    db, subject.id
                )
                subject_reports.append(report)
                total_pct += report.average_percentage * report.total_students
                total_students += report.total_students

                for zone, count in report.students_by_zone.items():
                    zone_distribution[zone] += count

            avg_pct = total_pct / total_students if total_students > 0 else 0.0

            return DepartmentReportSummary(
                department_id=department.id,
                department_name=department.name,
                total_students=total_students,
                average_attendance=round(avg_pct, 1),
                zone_distribution=zone_distribution,
                subjects=subject_reports,
            )

        except Exception as e:
            logger.error(f"Error generating department report: {e}")
            raise

    @staticmethod
    async def generate_weekly_summary(
        db: AsyncSession,
        week_start: date,
        week_end: date,
    ) -> WeeklyReportSummary:
        """Generate weekly attendance summary.

        Args:
            db: Database session.
            week_start: Start date of week.
            week_end: End date of week.

        Returns:
            WeeklyReportSummary.
        """
        try:
            # Load all sessions in week
            sessions_result = await db.execute(
                select(AttendanceSession).filter(
                    and_(
                        AttendanceSession.date >= week_start,
                        AttendanceSession.date <= week_end,
                    )
                )
            )
            sessions = sessions_result.scalars().all()
            total_sessions = len(sessions)

            # Count on-time vs late submissions
            submitted_on_time = sum(
                1 for s in sessions
                if s.submitted_at.date() == s.date
            )
            late_submissions = total_sessions - submitted_on_time
            missing_submissions = 0  # Would need timetable comparison

            # Calculate average attendance
            summaries_result = await db.execute(
                select(AttendanceSummary)
            )
            summaries = summaries_result.scalars().all()

            avg_pct = (
                sum(s.current_percentage for s in summaries) / len(summaries)
                if summaries
                else 0.0
            )

            zone_distribution = {
                "safe": sum(1 for s in summaries if s.zone == "safe"),
                "warning": sum(1 for s in summaries if s.zone == "warning"),
                "danger": sum(1 for s in summaries if s.zone == "danger"),
                "critical": sum(1 for s in summaries if s.zone == "critical"),
            }

            return WeeklyReportSummary(
                week_start=week_start,
                week_end=week_end,
                total_sessions=total_sessions,
                submitted_on_time=submitted_on_time,
                late_submissions=late_submissions,
                missing_submissions=missing_submissions,
                average_attendance=round(avg_pct, 1),
                zone_distribution=zone_distribution,
                anomalies=[],
            )

        except Exception as e:
            logger.error(f"Error generating weekly summary: {e}")
            raise
