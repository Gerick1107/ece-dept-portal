import { apiGet, apiPostJson } from "../../../services/api";

export type EceEveProject = {
  id: number;
  project_title: string;
  project_type: string;
  semesters: string;
  faculty_id: number | null;
  faculty_name?: string | null;
  guide_name: string | null;
  co_guide: string | null;
  course_code: string | null;
  course_name: string | null;
  admission_year: string | null;
  program_definition: string | null;
  program_specialization: string | null;
  student_roll_nos: string;
  student_names: string;
  credit: number | null;
};

export type EceEveProjectListResponse = {
  items: EceEveProject[];
  pagination: { page: number; page_size: number; total: number };
};

export type EceEveFilterOptions = {
  semesters: string[];
  course_codes: string[];
  course_names: string[];
  guide_names: string[];
  guides: { id: number; name: string }[];
  co_guides: string[];
  project_types: string[];
};

export type EceEveAnalyticsData = {
  total_count: number;
  by_branch: { branch: string; count: number }[];
  by_semester: { semester: string; count: number }[];
  by_type: { project_type: string; count: number }[];
  supervisor_distribution: { supervisor: string; count: number }[];
};

export function listEceEveProjects(params: {
  page?: number;
  page_size?: number;
  branch?: string;
  faculty_id?: number;
  guide_name?: string;
  student_name?: string;
  student_roll_no?: string;
  semesters?: string;
  course_codes?: string;
  course_name?: string;
  co_guide?: string;
  credit?: string;
  year?: string;
  project_type?: string;
  query?: string;
}) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") p.set(k, String(v));
  });
  const qs = p.toString();
  return apiGet<EceEveProjectListResponse>(`/ece-eve-projects${qs ? `?${qs}` : ""}`);
}

export function fetchEceEveProjectsAnalytics(branch?: string) {
  const qs = branch ? `?branch=${encodeURIComponent(branch)}` : "";
  return apiGet<EceEveAnalyticsData>(`/ece-eve-projects/analytics${qs}`);
}

export function fetchEceEveProjectFilters() {
  return apiGet<EceEveFilterOptions>("/ece-eve-projects/filters");
}

export async function downloadEceEveExport(
  params: Record<string, string | number | undefined>,
  format: "csv" | "xlsx" | "pdf"
) {
  const p = new URLSearchParams({ format });
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && String(v) !== "") p.set(k, String(v));
  });
  const token = localStorage.getItem("access_token");
  const apiBase = import.meta.env.VITE_API_BASE ?? "/api/v1";
  const res = await fetch(`${apiBase}/ece-eve-projects/export?${p.toString()}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `ece_eve_projects.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

export function purgeAllEceEveProjects() {
  return apiPostJson<{
    purged: boolean;
    standalone_removed: number;
    resynced_from_btp: number;
    removed_files: number;
  }>("/ece-eve-projects/admin/purge-all", {});
}
