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

import type { ContributionResource } from "../contributions/contributionConfig";

export type ContributionsListResponse = {
  items: Record<string, unknown>[];
  years: string[];
  exact_years: number[];
  faculty: { id: number; name: string }[];
  extra_filter_values: string[];
  unmatched_count: number;
};

export function listContributions(
  resource: ContributionResource,
  params?: {
    query?: string;
    year?: string;
    exact_year?: number;
    faculty_id?: number;
    extra_filter?: string;
    unmatched_only?: boolean;
  }
) {
  const p = new URLSearchParams();
  if (params?.query) p.set("query", params.query);
  if (params?.year) p.set("year", params.year);
  if (params?.exact_year != null) p.set("exact_year", String(params.exact_year));
  if (params?.faculty_id != null) p.set("faculty_id", String(params.faculty_id));
  if (params?.extra_filter) p.set("extra_filter", params.extra_filter);
  if (params?.unmatched_only) p.set("unmatched_only", "true");
  const s = p.toString();
  return apiGet<ContributionsListResponse>(`/contributions/${resource}${s ? `?${s}` : ""}`);
}

export function createContribution(resource: ContributionResource, body: Record<string, unknown>) {
  return apiPostJson<Record<string, unknown>>(`/contributions/${resource}`, body);
}

export function updateContribution(resource: ContributionResource, id: number, body: Record<string, unknown>) {
  const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
  return fetch(`${API_BASE}/contributions/${resource}/${id}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}`,
    },
    body: JSON.stringify(body),
  }).then(async (res) => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error((err as { detail?: string }).detail ?? "Update failed");
    }
    return res.json() as Promise<Record<string, unknown>>;
  });
}

export function deleteContribution(resource: ContributionResource, id: number) {
  return apiDelete(`/contributions/${resource}/${id}`);
}

export function resolveContributionFaculty(resource: ContributionResource, id: number, facultyId: number) {
  return apiPostJson<Record<string, unknown>>(`/contributions/${resource}/${id}/resolve-faculty`, {
    faculty_id: facultyId,
  });
}

export type ContributionsExportFilters = {
  query?: string;
  year?: string;
  exact_year?: number;
  exact_year_from?: number;
  exact_year_to?: number;
  faculty_id?: number;
  extra_filter?: string;
};

export async function downloadContributionsExport(resource: ContributionResource, filters: ContributionsExportFilters = {}) {
  const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
  const p = new URLSearchParams();
  if (filters.query) p.set("query", filters.query);
  if (filters.year) p.set("year", filters.year);
  if (filters.exact_year != null) p.set("exact_year", String(filters.exact_year));
  if (filters.exact_year_from != null) p.set("exact_year_from", String(filters.exact_year_from));
  if (filters.exact_year_to != null) p.set("exact_year_to", String(filters.exact_year_to));
  if (filters.faculty_id != null) p.set("faculty_id", String(filters.faculty_id));
  if (filters.extra_filter) p.set("extra_filter", filters.extra_filter);
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/contributions/${resource}/export?${p}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${resource}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}
