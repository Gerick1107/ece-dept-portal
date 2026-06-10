import { apiGet, apiPostJson } from "../../../services/api";

export type ComparisonRow = {
  metric: string;
  previous: number | null;
  current: number | null;
  delta: number | null;
  trend: "up" | "down" | "neutral";
};

export type AssessmentSummaryItem = {
  component_type: string;
  component_count: number;
  total_questions: number;
};

export type CourseComparison = {
  course_title: string;
  has_previous: boolean;
  current_semester: string;
  previous_semester: string | null;
  current_run_id: string;
  co_comparison: ComparisonRow[];
  po_comparison: ComparisonRow[];
  insufficient_history: boolean;
  co_descriptions_available: boolean;
  assessment_summary: AssessmentSummaryItem[];
};

export type InsightCourseOption = {
  course_title: string;
  semester_count: number;
  latest_semester: string;
  latest_run_id: string;
};

export type GenerateInsightsResponse = {
  course_title: string;
  run_id: string;
  comparison: CourseComparison | null;
  insights: string | null;
  generated_at: string | null;
  cached: boolean;
};

export function fetchInsightCourses() {
  return apiGet<{ success: boolean; data: { items: InsightCourseOption[] } }>("/llm-insights/courses").then(
    (r) => r.data.items
  );
}

export function fetchCourseComparison(courseTitle: string) {
  const p = new URLSearchParams({ course_title: courseTitle });
  return apiGet<{ success: boolean; data: CourseComparison }>(`/llm-insights/comparison?${p}`).then((r) => r.data);
}

export function fetchCachedInsights(courseTitle: string) {
  const p = new URLSearchParams({ course_title: courseTitle });
  return apiGet<{ success: boolean; data: GenerateInsightsResponse }>(`/llm-insights/cached?${p}`).then((r) => r.data);
}

export function generateLlmInsights(body: { course_title: string; regenerate?: boolean }) {
  return apiPostJson<{ success: boolean; data: GenerateInsightsResponse }>("/llm-insights/generate", body).then(
    (r) => r.data
  );
}
