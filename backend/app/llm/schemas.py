from __future__ import annotations

from pydantic import BaseModel, Field


class GenerateInsightsRequest(BaseModel):
    course_title: str = Field(min_length=1)
    run_id: str | None = None
    regenerate: bool = False


class ComparisonRow(BaseModel):
    metric: str
    previous: float | None = None
    current: float | None = None
    delta: float | None = None
    trend: str = "neutral"


class CourseComparison(BaseModel):
    course_title: str
    has_previous: bool
    current_semester: str
    previous_semester: str | None = None
    current_run_id: str
    co_comparison: list[ComparisonRow]
    po_comparison: list[ComparisonRow]
    insufficient_history: bool


class InsightCourseOption(BaseModel):
    course_title: str
    semester_count: int
    latest_semester: str
    latest_run_id: str


class GenerateInsightsResponse(BaseModel):
    course_title: str
    run_id: str
    comparison: CourseComparison | None = None
    insights: str | None = None
    generated_at: str | None = None
    cached: bool = False
