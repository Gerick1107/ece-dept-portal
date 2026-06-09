import { apiDelete, apiGet, apiPostJson } from "../../services/api";
import type { AwardsListResponse, CourseRecord, FacultyAward } from "../projects/types/projects";

export function listCourses() {
  return apiGet<{ courses: CourseRecord[] }>("/courses");
}

export function createCourse(courseCode: string, courseName: string) {
  return apiPostJson<CourseRecord>("/courses", { course_code: courseCode, course_name: courseName });
}

export function listAwards(query?: string, year?: string, exactYear?: number) {
  const p = new URLSearchParams();
  if (query) p.set("query", query);
  if (year) p.set("year", year);
  if (exactYear != null) p.set("exact_year", String(exactYear));
  const s = p.toString();
  return apiGet<AwardsListResponse>(`/awards${s ? `?${s}` : ""}`);
}

export type AwardFormBody = {
  faculty_name: string;
  year: string;
  exact_year?: number | null;
  awarded_by?: string | null;
  award: string;
};

export function createAward(body: AwardFormBody) {
  return apiPostJson<FacultyAward>("/awards", body);
}

export function updateAward(id: number, body: AwardFormBody) {
  const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
  return fetch(`${API_BASE}/awards/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}`,
    },
    body: JSON.stringify(body),
  }).then(async (res) => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? "Update failed");
    }
    return res.json() as Promise<FacultyAward>;
  });
}

export function deleteAward(id: number) {
  return apiDelete(`/awards/${id}`);
}

export type AwardsExportFilters = {
  query?: string;
  year?: string;
  exact_year?: number;
  exact_year_from?: number;
  exact_year_to?: number;
  year_from?: string;
  year_to?: string;
  faculty_names?: string[];
};

export async function downloadAwardsExport(filters: AwardsExportFilters = {}) {
  const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
  const p = new URLSearchParams();
  if (filters.query) p.set("query", filters.query);
  if (filters.year) p.set("year", filters.year);
  if (filters.exact_year != null) p.set("exact_year", String(filters.exact_year));
  if (filters.exact_year_from != null) p.set("exact_year_from", String(filters.exact_year_from));
  if (filters.exact_year_to != null) p.set("exact_year_to", String(filters.exact_year_to));
  if (filters.year_from) p.set("year_from", filters.year_from);
  if (filters.year_to) p.set("year_to", filters.year_to);
  if (filters.faculty_names?.length) p.set("faculty_names", filters.faculty_names.join(","));
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/awards/export?${p}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Export failed");
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "faculty_awards.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}
