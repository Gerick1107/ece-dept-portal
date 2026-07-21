import { apiDelete, apiGet, apiPostJson, apiPutJson } from "../../services/api";

export type Lab = {
  id: number;
  lab_name: string;
  location: string | null;
  faculty_id: number;
  faculty_name: string | null;
  total_seats: number;
  allotted_seats: number;
  remaining_seats: number;
  occupancy_pct: number;
  remarks: string | null;
  updated_at: string | null;
};

export type LabSummary = {
  total_labs: number;
  total_seats: number;
  allotted_seats: number;
  remaining_seats: number;
  occupancy_pct: number;
};

export type LabFormBody = {
  lab_name: string;
  location?: string | null;
  faculty_id: number;
  total_seats: number;
  allotted_seats: number;
  remarks?: string | null;
};

export function listLabs(params?: { faculty_id?: number; query?: string }) {
  const q = new URLSearchParams();
  if (params?.faculty_id) q.set("faculty_id", String(params.faculty_id));
  if (params?.query) q.set("query", params.query);
  const s = q.toString();
  return apiGet<{ items: Lab[]; summary: LabSummary }>(`/labs${s ? `?${s}` : ""}`);
}

export function getFacultyOptions() {
  return apiGet<{ faculty: { id: number; name: string }[] }>("/labs/faculty-options");
}

export function createLab(body: LabFormBody) {
  return apiPostJson<Lab>("/labs", body);
}

export function updateLab(id: number, body: LabFormBody) {
  return apiPutJson<Lab>(`/labs/${id}`, body);
}

export function deleteLab(id: number) {
  return apiDelete(`/labs/${id}`);
}