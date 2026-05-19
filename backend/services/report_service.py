"""Report generation service.

Generates attendance reports for subjects, departments, and system-wide.
"""

import logging
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from backend.models.attendance_summary import AttendanceSummary, AttendanceZone
from backend.models.subject import Subject
from backend.models.student import Student
from backend.models.department import Department
from backend.models.faculty import Faculty
from backend.models.user import User
from backend.schemas.report import (
    SubjectReportRow,
    SubjectAttendanceReport,
    DepartmentReportSummary,
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
            SubjectAttendanceReport.
        """
        try:
            # Load subject
            subject_result = await db.execute(
                select(Subject).filter(Subject.id == subject_id)
            )
            subject = subject_result.scalar_one()

            # Load faculty name
            faculty_name = "Unassigned"
            if subject.faculty_id:
                faculty_result = await db.execute(
                    select(User).filter(
                        User.id.in_(
                            select(Faculty.user_id).filter(
                                Faculty.id == subject.faculty_id
                            )
                        )
                    )
                )
                faculty = faculty_result.scalar()
                if faculty:
                    faculty_name = faculty.full_name

            # Load all summaries for subject
            summaries_result = await db.execute(
                select(AttendanceSummary).filter(
                    AttendanceSummary.subject_id == subject_id
                )
            )
            summaries = summaries_result.scalars().all()

            # Build report rows
            rows: list[SubjectReportRow] = []
            total_percentage = 0.0
            zone_counts = {"safe": 0, "warning": 0, "danger": 0, "critical": 0}

            for summary in summaries:
                # Load student name
                student_result = await db.execute(
                    select(Student).filter(Student.id == summary.student_id)
                )
                student = student_result.scalar_one()

                row = SubjectReportRow(
                    student_id=student.id,
                    full_name=student.user.full_name if student.user else "Unknown",
                    roll_number=student.roll_number,
                    classes_attended=summary.classes_attended,
                    classes_held=summary.classes_held,
                    percentage=summary.current_percentage,
                    zone=summary.zone,
                )
                rows.append(row)
                total_percentage += summary.current_percentage
                zone_counts[summary.zone] = zone_counts.get(summary.zone, 0) + 1

            # Calculate averages
            avg_percentage = (
                total_percentage / len(summaries) if summaries else 0.0
            )

            return SubjectAttendanceReport(
                subject_id=subject.id,
                subject_name=subject.name,
                faculty_name=faculty_name,
                total_students=len(summaries),
                average_percentage=round(avg_percentage, 1),
                students_by_zone=zone_counts,
                rows=rows,
            )

        except Exception as e:
            logger.error(f"Error generating subject report for {subject_id}: {e}")
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
            DepartmentReportSummary.
        """
        try:
            # Load department
            dept_result = await db.execute(
                select(Department).filter(Department.id == department_id)
            )
            department = dept_result.scalar_one()

            # Load all subjects in department
            subjects_result = await db.execute(
                select(Subject).filter(
                    and_(
                        Subject.department_id == department_id,
                        Subject.is_active == True,
                    )
                )
            )
            subjects = subjects_result.scalars().all()

            # Generate report for each subject
            subject_reports = []
            total_students = 0
            all_percentages = []
            all_zone_counts = {"safe": 0, "warning": 0, "danger": 0, "critical": 0}

            for subject in subjects:
                subject_report = await ReportService.generate_subject_report(
                    db, subject.id
                )
                subject_reports.append(subject_report)
                total_students += subject_report.total_students
                all_percentages.extend(
                    [row.percentage for row in subject_report.rows]
                )
                for zone, count in subject_report.students_by_zone.items():
                    all_zone_counts[zone] = all_zone_counts.get(zone, 0) + count

            # Calculate department averages
            avg_attendance = (
                sum(all_percentages) / len(all_percentages)
                if all_percentages
                else 0.0
            )

            return DepartmentReportSummary(
                department_id=department.id,
                department_name=department.name,
                total_students=total_students,
                average_attendance=round(avg_attendance, 1),
                zone_distribution=all_zone_counts,
                subjects=subject_reports,
            )

        except Exception as e:
            logger.error(f"Error generating department report: {e}")
            raise
