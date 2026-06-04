import { apiDelete, apiGet, apiPostJson } from "../../services/api";
import type { AwardsListResponse, CourseRecord, FacultyAward } from "../projects/types/projects";

export function listCourses() {
  return apiGet<{ courses: CourseRecord[] }>("/courses");
}

export function createCourse(courseCode: string, courseName: string) {
  return apiPostJson<CourseRecord>("/courses", { course_code: courseCode, course_name: courseName });
}

export function listAwards(query?: string, year?: string) {
  const p = new URLSearchParams();
  if (query) p.set("query", query);
  if (year) p.set("year", year);
  const s = p.toString();
  return apiGet<AwardsListResponse>(`/awards${s ? `?${s}` : ""}`);
}

export function createAward(body: { faculty_name: string; year: string; award: string }) {
  return apiPostJson<FacultyAward>("/awards", body);
}

export function updateAward(id: number, body: { faculty_name: string; year: string; award: string }) {
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
