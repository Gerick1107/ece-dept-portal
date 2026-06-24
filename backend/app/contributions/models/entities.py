from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class _ContributionBase:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    faculty_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    faculty_id: Mapped[int | None] = mapped_column(
        ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True, index=True
    )
    year: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    exact_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class FacultyMembership(Base, _ContributionBase):
    __tablename__ = "faculty_memberships"

    society_name: Mapped[str] = mapped_column(String(500), nullable=False)
    grade_position: Mapped[str] = mapped_column(String(200), nullable=False)


class FacultyResourcePersonEvent(Base, _ContributionBase):
    __tablename__ = "faculty_resource_person_events"

    program_name: Mapped[str] = mapped_column(String(500), nullable=False)
    event_date: Mapped[str] = mapped_column(String(128), nullable=False)
    location: Mapped[str] = mapped_column(String(500), nullable=False)
    organized_by: Mapped[str] = mapped_column(String(500), nullable=False)


class FacultyMoocDevelopment(Base, _ContributionBase):
    __tablename__ = "faculty_mooc_development"

    course_name: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str] = mapped_column(String(200), nullable=False)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)


class DepartmentFdpEvent(Base, _ContributionBase):
    __tablename__ = "department_fdp_events"

    program_name: Mapped[str] = mapped_column(String(500), nullable=False)
    event_date: Mapped[str] = mapped_column(String(128), nullable=False)
    duration: Mapped[str] = mapped_column(String(128), nullable=False)
    speaker_affiliation: Mapped[str | None] = mapped_column(String(500), nullable=True)
    co_speakers: Mapped[str | None] = mapped_column(Text, nullable=True)
    no_of_attendees: Mapped[int | None] = mapped_column(Integer, nullable=True)


class FacultyStudentProjectSupport(Base, _ContributionBase):
    __tablename__ = "faculty_student_project_support"

    event_name: Mapped[str] = mapped_column(String(500), nullable=False)
    event_date: Mapped[str] = mapped_column(String(128), nullable=False)
    place: Mapped[str] = mapped_column(String(500), nullable=False)
    website_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)


class FacultyCollaboration(Base, _ContributionBase):
    __tablename__ = "faculty_collaborations"

    collaboration_type: Mapped[str] = mapped_column(String(200), nullable=False)
    company_place: Mapped[str] = mapped_column(String(500), nullable=False)
    duration: Mapped[str] = mapped_column(String(128), nullable=False)
    outcomes: Mapped[str] = mapped_column(Text, nullable=False)


class FacultyService(Base, _ContributionBase):
    __tablename__ = "faculty_services"

    scope: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    role_title: Mapped[str] = mapped_column(String(500), nullable=False)
    organization: Mapped[str | None] = mapped_column(String(500), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    duration_text: Mapped[str | None] = mapped_column(String(128), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class PhdStudent(Base):
    __tablename__ = "phd_students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    faculty_name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    faculty_id: Mapped[int | None] = mapped_column(
        ForeignKey("faculty.id", ondelete="SET NULL"), nullable=True, index=True
    )
    as_of_year: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    students_graduated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ongoing_phd_students: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


CONTRIBUTION_MODELS = {
    "memberships": FacultyMembership,
    "resource-person-events": FacultyResourcePersonEvent,
    "mooc-development": FacultyMoocDevelopment,
    "department-fdp-events": DepartmentFdpEvent,
    "student-project-support": FacultyStudentProjectSupport,
    "collaborations": FacultyCollaboration,
    "faculty-services": FacultyService,
    "phd-students": PhdStudent,
}
