"""Pydantic schemas for subject/department management."""

from pydantic import BaseModel, Field
from datetime import time


class DepartmentCreate(BaseModel):
    """Create department schema."""
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)


class DepartmentResponse(BaseModel):
    """Department response schema."""
    id: int
    name: str
    code: str

    class Config:
        from_attributes = True


class SubjectCreate(BaseModel):
    """Create subject schema."""
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)
    department_id: int
    faculty_id: int | None = None
    attendance_threshold: float = Field(default=75.0, ge=0, le=100)
    total_planned_classes: int = Field(default=40, ge=1)
    semester: int = Field(..., ge=1, le=8)


class SubjectResponse(BaseModel):
    """Subject response schema."""
    id: int
    name: str
    code: str
    department_id: int
    faculty_id: int | None
    attendance_threshold: float
    total_planned_classes: int
    semester: int
    is_active: bool

    class Config:
        from_attributes = True


class SubjectUpdate(BaseModel):
    """Update subject schema."""
    name: str | None = Field(None, min_length=2, max_length=255)
    faculty_id: int | None = None
    attendance_threshold: float | None = Field(None, ge=0, le=100)
    total_planned_classes: int | None = Field(None, ge=1)
    is_active: bool | None = None


class TimetableCreate(BaseModel):
    """Create timetable entry schema."""
    subject_id: int
    day_of_week: str = Field(
        ...,
        description="Monday, Tuesday, ..., Sunday"
    )
    start_time: time
    end_time: time
    room: str = Field(..., max_length=50)


class TimetableResponse(BaseModel):
    """Timetable response schema."""
    id: int
    subject_id: int
    day_of_week: str
    start_time: time
    end_time: time
    room: str
    is_active: bool

    class Config:
        from_attributes = True


class StudentCreate(BaseModel):
    """Create student schema."""
    user_id: int
    roll_number: str = Field(..., min_length=1, max_length=50)
    semester: int = Field(..., ge=1, le=8)
    department_id: int


class StudentResponse(BaseModel):
    """Student response schema."""
    id: int
    user_id: int
    full_name: str
    roll_number: str
    semester: int
    department_id: int

    class Config:
        from_attributes = True


class FacultyCreate(BaseModel):
    """Create faculty schema."""
    user_id: int
    employee_id: str = Field(..., min_length=1, max_length=50)
    department_id: int


class FacultyResponse(BaseModel):
    """Faculty response schema."""
    id: int
    user_id: int
    full_name: str
    employee_id: str
    department_id: int

    class Config:
        from_attributes = True
