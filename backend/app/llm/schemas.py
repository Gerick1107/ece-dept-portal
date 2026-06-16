from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateInsightsRequest(BaseModel):
    course_title: str = Field(min_length=1)
    run_id: str | None = None
    regenerate: bool = False
    current_semester: str | None = None
    current_section: str | None = None
    previous_semester: str | None = None
    previous_section: str | None = None


class AssessmentSummaryItem(BaseModel):
    component_type: str
    component_count: int
    total_questions: int


class AssessmentCoEntry(BaseModel):
    co_label: str
    question_count: int | None = None
    attainment: float | None = None


class AssessmentDetail(BaseModel):
    assessment_id: int | None = None
    name: str
    type: str | None = None
    semester: str | None = None
    section_label: str | None = None
    course_title: str | None = None
    cos: list[AssessmentCoEntry] = Field(default_factory=list)


class ComparisonRow(BaseModel):
    metric: str
    previous: float | None = None
    current: float | None = None
    delta: float | None = None
    trend: str = "neutral"


class CourseComparison(BaseModel):
    course_title: str
    course_key: str | None = None
    section_label: str | None = None
    has_previous: bool
    current_semester: str
    previous_semester: str | None = None
    current_section: str | None = None
    previous_section: str | None = None
    current_run_id: str
    previous_run_id: str | None = None
    co_comparison: list[ComparisonRow]
    po_comparison: list[ComparisonRow]
    insufficient_history: bool
    co_descriptions_available: bool = False
    assessment_summary: list[AssessmentSummaryItem] = Field(default_factory=list)
    previous_assessment_summary: list[AssessmentSummaryItem] = Field(default_factory=list)
    current_assessments: list[AssessmentDetail] = Field(default_factory=list)
    previous_assessments: list[AssessmentDetail] = Field(default_factory=list)
    available_semesters: list[str] = Field(default_factory=list)
    available_sections: list[str] = Field(default_factory=list)


class InsightCourseOption(BaseModel):
    course_title: str
    course_key: str
    section_label: str | None = None
    semester_count: int
    semesters: list[str] = Field(default_factory=list)
    latest_semester: str
    latest_run_id: str


class GenerateInsightsResponse(BaseModel):
    course_title: str
    run_id: str
    comparison: CourseComparison | None = None
    insights: str | None = None
    generated_at: str | None = None
    cached: bool = False
