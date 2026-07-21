import { apiDelete, apiGet, apiPostJson, apiPutJson } from "../../services/api";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// --- Courses ---------------------------------------------------------

export type ModerationCourse = {
  id: number;
  course_code: string;
  course_name: string;
  paper_count: number;
  faculty_names: string[];
};

export function listModerationCourses(params?: { query?: string; faculty?: string }) {
  const q = new URLSearchParams();
  if (params?.query) q.set("query", params.query);
  if (params?.faculty) q.set("faculty", params.faculty);
  const s = q.toString();
  return apiGet<{ items: ModerationCourse[] }>(`/moderation/courses${s ? `?${s}` : ""}`);
}

export function getModerationCourse(id: number) {
  return apiGet<ModerationCourse>(`/moderation/courses/${id}`);
}

export function createModerationCourse(body: { course_code: string; course_name: string }) {
  return apiPostJson<ModerationCourse>("/moderation/courses", body);
}

export function updateModerationCourse(id: number, body: { course_code: string; course_name: string }) {
  return apiPutJson<ModerationCourse>(`/moderation/courses/${id}`, body);
}

export function deleteModerationCourse(id: number) {
  return apiDelete(`/moderation/courses/${id}`);
}

// --- Question papers ---------------------------------------------------

export type QuestionPaper = {
  id: number;
  course_id: number;
  faculty_name: string;
  year: number;
  semester: "Winter" | "Monsoon";
  original_filename: string;
  uploaded_at: string | null;
};

export function listCoursePapers(
  courseId: number,
  params?: { year?: number; sort?: "asc" | "desc" }
) {
  const q = new URLSearchParams();
  if (params?.year) q.set("year", String(params.year));
  if (params?.sort) q.set("sort", params.sort);
  const s = q.toString();
  return apiGet<{ items: QuestionPaper[]; years: number[] }>(
    `/moderation/courses/${courseId}/papers${s ? `?${s}` : ""}`
  );
}

export async function uploadCoursePaper(
  courseId: number,
  form: { faculty_name: string; year: number; semester: "Winter" | "Monsoon"; file: File }
) {
  const fd = new FormData();
  fd.append("faculty_name", form.faculty_name);
  fd.append("year", String(form.year));
  fd.append("semester", form.semester);
  fd.append("file", form.file);
  const res = await fetch(`${API_BASE}/moderation/courses/${courseId}/papers`, {
    method: "POST",
    headers: authHeaders(),
    body: fd,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Upload failed");
  }
  return res.json() as Promise<QuestionPaper>;
}

export async function downloadPaper(paperId: number, filename: string) {
  const res = await fetch(`${API_BASE}/moderation/papers/${paperId}/download`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function deletePaper(paperId: number) {
  return apiDelete(`/moderation/papers/${paperId}`);
}

// --- Grade summary (unchanged) ------------------------------------------

export type GradeCriterion = {
  id: number;
  course_code: string;
  semester: string;
  grade_letter: string;
  min_marks: number;
  max_marks: number;
  remarks: string | null;
};

export function listGradeCriteria(params?: { course_code?: string; semester?: string }) {
  const q = new URLSearchParams();
  if (params?.course_code) q.set("course_code", params.course_code);
  if (params?.semester) q.set("semester", params.semester);
  const s = q.toString();
  return apiGet<{ items: GradeCriterion[] }>(`/moderation/grade-summary${s ? `?${s}` : ""}`);
}

export function createGradeCriterion(body: Omit<GradeCriterion, "id">) {
  return apiPostJson<GradeCriterion>("/moderation/grade-summary", body);
}

export function updateGradeCriterion(id: number, body: Omit<GradeCriterion, "id">) {
  return apiPutJson<GradeCriterion>(`/moderation/grade-summary/${id}`, body);
}

export function deleteGradeCriterion(id: number) {
  return apiDelete(`/moderation/grade-summary/${id}`);
}