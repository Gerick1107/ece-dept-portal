import { apiDelete, apiGet, apiPostJson } from "../../../services/api";

export type AllocationCourse = {
  id: number;
  faculty_name: string;
  faculty_id: number | null;
  semester: string;
  academic_year: string;
  course_code: string;
  course_name: string;
  ug_pg: string;
  core_elective: string;
  is_first_year: boolean;
  first_year_course_name: string | null;
};

export type FacultyAllocationRow = {
  faculty_id: number;
  faculty_name: string;
  courses: AllocationCourse[];
  has_courses: boolean;
};

export type AllocationListResponse = {
  faculty_rows: FacultyAllocationRow[];
  unassigned: AllocationCourse[];
  unmatched: AllocationCourse[];
  semesters: string[];
  academic_years: string[];
};

export type DashboardSummary = {
  semester: string;
  faculty_teaching: number;
  total_courses: number;
  ug_courses: number;
  pg_courses: number;
  ug_pg_courses: number;
  core_courses: number;
  elective_courses: number;
  first_year_courses: number;
  unassigned: number;
};

export function getCurrentSemester() {
  return apiGet<{ semester: string }>("/course-allocation/current-semester");
}

export function getAllocationDashboardSummary(semester?: string) {
  const p = semester ? `?semester=${encodeURIComponent(semester)}` : "";
  return apiGet<DashboardSummary>(`/course-allocation/dashboard-summary${p}`);
}

export function listAllocations(params?: {
  scope?: string;
  query?: string;
  ug_pg?: string;
  core_elective?: string;
  first_year_only?: boolean;
}) {
  const q = new URLSearchParams();
  if (params?.scope) q.set("scope", params.scope);
  if (params?.query) q.set("query", params.query);
  if (params?.ug_pg) q.set("ug_pg", params.ug_pg);
  if (params?.core_elective) q.set("core_elective", params.core_elective);
  if (params?.first_year_only) q.set("first_year_only", "true");
  const s = q.toString();
  return apiGet<AllocationListResponse>(`/course-allocation${s ? `?${s}` : ""}`);
}

export type FacultyAllocationHistory = {
  faculty: { id: number; name: string };
  history: AllocationCourse[];
  course_counts: Array<{
    course_code: string;
    course_name: string;
    times_taught: number;
    semesters: string[];
    most_recent_semester: string;
  }>;
  first_year_counts: Array<{ name: string; count: number }>;
  analytics: {
    courses_per_semester: Array<{ semester: string; count: number }>;
    ug_pg_split: Record<string, number>;
    core_elective_split: Record<string, number>;
  };
};

export function getFacultyAllocationHistory(facultyId: number) {
  return apiGet<FacultyAllocationHistory>(`/course-allocation/faculty/${facultyId}`);
}

export async function downloadAllocationsExport(scope?: string) {
  const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
  const q = scope ? `?scope=${encodeURIComponent(scope)}` : "";
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/course-allocation/export${q}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "course_allocations.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

export function resolveAllocationFaculty(rowId: number, facultyId: number) {
  return apiPostJson(`/course-allocation/${rowId}/resolve-faculty`, { faculty_id: facultyId });
}

export function deleteAllocation(rowId: number) {
  return apiDelete(`/course-allocation/${rowId}`);
}
