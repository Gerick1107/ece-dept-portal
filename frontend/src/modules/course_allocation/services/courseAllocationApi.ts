import { apiDelete, apiGet, apiPostJson, apiPutJson } from "../../../services/api";

export type AllocationCourse = {
  id: number;
  faculty_name: string;
  faculty_id: number | null;
  semester: string;
  academic_year: string;
  course_code: string;
  course_name: string;
  ug_type: string | null;
  pg_type: string | null;
  registered_students: number | null;
  source?: string;
  is_faculty_placeholder?: boolean;
  course_catalog_id?: number | null;
};

export type AllocationWritePayload = {
  faculty_name?: string;
  faculty_id?: number | null;
  semester: string;
  academic_year?: string;
  course_code: string;
  course_name: string;
  ug_type?: string | null;
  pg_type?: string | null;
  registered_students?: number | null;
  clear_registered_students?: boolean;
  course_catalog_id?: number | null;
  source?: string;
  is_faculty_placeholder?: boolean;
  clear_faculty?: boolean;
};

export type CatalogEntry = {
  id: number;
  course_code: string;
  course_name: string;
  ug_type: string | null;
  pg_type: string | null;
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
  ug_and_pg_courses: number;
  ug_type_split: Record<string, number>;
  pg_type_split: Record<string, number>;
  unassigned: number;
  missing_registered_students: number;
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
  ug_type?: string;
  pg_type?: string;
}) {
  const q = new URLSearchParams();
  if (params?.scope) q.set("scope", params.scope);
  if (params?.query) q.set("query", params.query);
  if (params?.ug_type) q.set("ug_type", params.ug_type);
  if (params?.pg_type) q.set("pg_type", params.pg_type);
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
  analytics: {
    courses_per_semester: Array<{ semester: string; count: number }>;
    ug_type_split: Record<string, number>;
    pg_type_split: Record<string, number>;
  };
};

export function getFacultyAllocationHistory(facultyId: number) {
  return apiGet<FacultyAllocationHistory>(`/course-allocation/faculty/${facultyId}`);
}

export type CourseAllocationRow = {
  course_key: string;
  course_catalog_id: number | null;
  course_code: string;
  course_name: string;
  allocations: AllocationCourse[];
  has_allocations: boolean;
};

export type CourseListResponse = {
  course_rows: CourseAllocationRow[];
  semesters: string[];
  academic_years: string[];
};

export type CoursesDashboardSummary = {
  semester: string;
  total_courses: number;
  faculty_involved: number;
  ug_courses: number;
  pg_courses: number;
  ug_and_pg_courses: number;
  ug_type_split: Record<string, number>;
  pg_type_split: Record<string, number>;
  missing_registered_students: number;
};

export type CourseAllocationHistory = {
  course: { id: number; course_code: string; course_name: string };
  history: AllocationCourse[];
  faculty_counts: Array<{
    faculty_id: number | null;
    faculty_name: string;
    times_taught: number;
    semesters: string[];
    most_recent_semester: string;
  }>;
  analytics: {
    instances_per_semester: Array<{ semester: string; count: number }>;
    ug_type_split: Record<string, number>;
    pg_type_split: Record<string, number>;
  };
};

export function listCoursesAllocations(params?: {
  scope?: string;
  query?: string;
  ug_type?: string;
  pg_type?: string;
}) {
  const q = new URLSearchParams();
  if (params?.scope) q.set("scope", params.scope);
  if (params?.query) q.set("query", params.query);
  if (params?.ug_type) q.set("ug_type", params.ug_type);
  if (params?.pg_type) q.set("pg_type", params.pg_type);
  const s = q.toString();
  return apiGet<CourseListResponse>(`/course-allocation/courses${s ? `?${s}` : ""}`);
}

export function getCoursesDashboardSummary(semester?: string) {
  const p = semester ? `?semester=${encodeURIComponent(semester)}` : "";
  return apiGet<CoursesDashboardSummary>(`/course-allocation/courses/dashboard-summary${p}`);
}

export function getCourseAllocationHistory(courseCatalogId: number) {
  return apiGet<CourseAllocationHistory>(`/course-allocation/courses/${courseCatalogId}`);
}

export async function downloadCoursesAllocationsExport(scope?: string) {
  const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
  const q = scope ? `?scope=${encodeURIComponent(scope)}` : "";
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/course-allocation/courses/export${q}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "course_wise_allocations.xlsx";
  a.click();
  URL.revokeObjectURL(url);
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
  return apiPostJson<AllocationCourse>(`/course-allocation/${rowId}/resolve-faculty`, {
    faculty_id: facultyId,
  });
}

export function createAllocation(payload: AllocationWritePayload) {
  return apiPostJson<AllocationCourse>("/course-allocation", payload);
}

export function updateAllocation(rowId: number, payload: Partial<AllocationWritePayload>) {
  return apiPutJson<AllocationCourse>(`/course-allocation/${rowId}`, payload);
}

export function deleteAllocation(rowId: number) {
  return apiDelete(`/course-allocation/${rowId}`);
}

export function listCourseCatalog() {
  return apiGet<{ items: CatalogEntry[] }>("/course-allocation/catalog");
}

export function updateCatalogEntry(entryId: number, payload: Partial<CatalogEntry>) {
  return apiPutJson<CatalogEntry>(`/course-allocation/catalog/${entryId}`, payload);
}
