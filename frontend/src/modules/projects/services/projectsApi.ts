import { apiDelete, apiGet, apiPostForm, apiPostJson } from "../../../services/api";
import type { Project, ProjectFilterOptions, ProjectListResponse, SdgCatalogItem } from "../types/projects";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

export type ProjectFilters = {
  page?: number;
  page_size?: number;
  query?: string;
  faculty_id?: number;
  project_type?: string;
  semester?: string;
  semesters?: string;
  course_code?: string;
  course_codes?: string;
  course_name?: string;
  co_guide?: string;
  student_name?: string;
  student_roll_no?: string;
  sdg?: number;
  credit?: string;
  confirmed_sdg_only?: boolean;
};

function qs(filters: ProjectFilters): string {
  const p = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : "";
}

export function listProjects(filters: ProjectFilters = {}) {
  return apiGet<ProjectListResponse>(`/projects/search${qs(filters)}`);
}

export function getProjectFilters() {
  return apiGet<ProjectFilterOptions>("/projects/filters");
}

export function listSdgCatalog() {
  return apiGet<SdgCatalogItem[]>("/projects/sdgs/catalog");
}

export function getProjectSettings() {
  return apiGet<{ enable_sdg_llm: boolean }>("/projects/settings");
}

export function createProject(body: Record<string, unknown>) {
  return apiPostJson<Project>("/projects", body);
}

export function updateProject(id: number, body: Record<string, unknown>) {
  return fetch(`${API_BASE}/projects/${id}`, {
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
    return res.json() as Promise<Project>;
  });
}

export function deleteProject(id: number) {
  return apiDelete(`/projects/${id}`);
}

export function importProjects(file: File, semesterTag: string, autoSdg = true) {
  const form = new FormData();
  form.append("file", file);
  const tag = encodeURIComponent(semesterTag);
  return apiPostForm<import("../types/projects").ImportSummary>(
    `/projects/import?auto_sdg=${autoSdg}&semester_tag=${tag}`,
    form
  );
}

export function generateSdgs(projectId: number) {
  return apiPostJson<Project>(`/projects/${projectId}/generate-sdgs`, {});
}

export function acceptSdgs(projectId: number, sdgNumbers: number[]) {
  return apiPostJson<Project>(`/projects/${projectId}/accept-sdgs`, { sdg_numbers: sdgNumbers });
}

export function rejectSdgs(projectId: number) {
  return apiPostJson<Project>(`/projects/${projectId}/reject-sdgs`, {});
}

export function editSdgs(projectId: number, sdgNumbers: number[]) {
  return apiPostJson<Project>(`/projects/${projectId}/edit-sdgs`, { sdg_numbers: sdgNumbers });
}

export type BulkSdgPreview = {
  faculty_id: number;
  from_semester: string;
  to_semester: string;
  count: number;
  projects: Array<{
    id: number;
    project_title: string;
    semesters: string[];
    sdg_numbers: number[];
  }>;
};

export function previewBulkAcceptSdgs(body: { faculty_id: number; from_semester: string; to_semester: string }) {
  return apiPostJson<BulkSdgPreview>("/projects/bulk-accept-sdgs/preview", body);
}

export function bulkAcceptSdgs(body: { faculty_id: number; from_semester: string; to_semester: string }) {
  return apiPostJson<{
    accepted_count: number;
    accepted_project_ids: number[];
    accepted_at: string;
    accepted_by: string | null;
  }>("/projects/bulk-accept-sdgs", body);
}

export async function downloadProjectExport(filters: ProjectFilters, format: "csv" | "xlsx" | "pdf") {
  const p = new URLSearchParams({ format, ...Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== null && v !== "")
      .map(([k, v]) => [k, String(v)])
  ) });
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/projects/export?${p}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `projects.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

export async function downloadImportTemplate() {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/projects/template`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Template download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "btp_ip_import_template.xlsx";
  a.click();
  URL.revokeObjectURL(url);
}

export function purgeAllProjects() {
  return apiPostJson<{ purged: boolean; removed_files: number }>("/projects/admin/purge-all", {});
}

export function listProjectUploads() {
  return apiGet<{ project_uploads: import("../types/projects").ProjectUploadRow[] }>(
    "/projects/admin/uploads"
  );
}

export async function downloadProjectUpload(uploadId: number) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/projects/admin/uploads/${uploadId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `project_upload_${uploadId}.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

export function deleteProjectUpload(uploadId: number) {
  return apiDelete(`/projects/admin/uploads/${uploadId}`);
}
