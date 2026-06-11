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
  course_key?: string;
  section_label?: string | null;
  has_previous: boolean;
  current_semester: string;
  previous_semester: string | null;
  current_section?: string | null;
  previous_section?: string | null;
  current_run_id: string;
  previous_run_id?: string | null;
  co_comparison: ComparisonRow[];
  po_comparison: ComparisonRow[];
  insufficient_history: boolean;
  co_descriptions_available: boolean;
  assessment_summary: AssessmentSummaryItem[];
  available_semesters: string[];
  available_sections: string[];
};

export type InsightCourseOption = {
  course_title: string;
  course_key: string;
  section_label?: string | null;
  semester_count: number;
  semesters: string[];
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

export type ComparisonParams = {
  course_title: string;
  current_semester?: string;
  current_section?: string;
  previous_semester?: string;
  previous_section?: string;
};

function comparisonQuery(params: ComparisonParams) {
  const p = new URLSearchParams({ course_title: params.course_title });
  if (params.current_semester) p.set("current_semester", params.current_semester);
  if (params.current_section) p.set("current_section", params.current_section);
  if (params.previous_semester) p.set("previous_semester", params.previous_semester);
  if (params.previous_section) p.set("previous_section", params.previous_section);
  return p;
}

export function fetchInsightCourses() {
  return apiGet<{ success: boolean; data: { items: InsightCourseOption[] } }>("/llm-insights/courses").then(
    (r) => r.data.items
  );
}

export function fetchCourseComparison(params: ComparisonParams) {
  const p = comparisonQuery(params);
  return apiGet<{ success: boolean; data: CourseComparison }>(`/llm-insights/comparison?${p}`).then((r) => r.data);
}

export function fetchCachedInsights(params: ComparisonParams) {
  const p = comparisonQuery(params);
  return apiGet<{ success: boolean; data: GenerateInsightsResponse }>(`/llm-insights/cached?${p}`).then((r) => r.data);
}

export function generateLlmInsights(
  body: ComparisonParams & { regenerate?: boolean; run_id?: string }
) {
  return apiPostJson<{ success: boolean; data: GenerateInsightsResponse }>("/llm-insights/generate", body).then(
    (r) => r.data
  );
}
