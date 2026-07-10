import { apiDelete, apiGet, apiPatchJson, apiPostJson } from "../../../services/api";
import type { Faculty, PaginationMeta, Publication } from "../types/publications";

export type CustomColumn = {
  id: number;
  key: string;
  label: string;
  description: string | null;
  source_keys: string | null;
  crossref_field: string | null;
  use_llm: boolean;
  enabled: boolean;
};

export type CustomColumnInput = {
  label: string;
  description?: string | null;
  source_keys?: string | null;
  crossref_field?: string | null;
  use_llm?: boolean;
};

export type ScrapeLogEntry = {
  id: number;
  faculty_id: number;
  faculty_name?: string;
  status: string;
  new_publications_added: number;
  started_at: string;
  completed_at: string | null;
  errors: string | null;
};

export async function listFaculty(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  department?: string;
  include_inactive?: boolean;
}): Promise<{ items: Faculty[]; pagination: PaginationMeta }> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  if (params?.search) qs.set("search", params.search);
  if (params?.department) qs.set("department", params.department);
  if (params?.include_inactive) qs.set("include_inactive", "true");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet(`/publications/faculty${suffix}`);
}

const MAX_PAGE_SIZE = 200;

export async function listPublications(params?: {
  page?: number;
  page_size?: number;
  query?: string;
  faculty_id?: number;
  publication_year?: number;
  is_patent?: boolean;
}): Promise<{ items: Publication[]; pagination: PaginationMeta }> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  const pageSize = Math.min(params?.page_size ?? MAX_PAGE_SIZE, MAX_PAGE_SIZE);
  qs.set("page_size", String(pageSize));
  if (params?.query) qs.set("query", params.query);
  if (params?.faculty_id) qs.set("faculty_id", String(params.faculty_id));
  if (params?.publication_year) qs.set("publication_year", String(params.publication_year));
  if (params?.is_patent !== undefined) qs.set("is_patent", params.is_patent ? "true" : "false");
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet(`/publications/publications${suffix}`);
}

/** Fetch every page (API caps page_size at 200). */
export async function listAllPublications(params?: {
  query?: string;
  faculty_id?: number;
  publication_year?: number;
  is_patent?: boolean;
}): Promise<Publication[]> {
  const all: Publication[] = [];
  let page = 1;
  let total = 0;
  do {
    const response = await listPublications({ ...params, page, page_size: MAX_PAGE_SIZE });
    all.push(...response.items);
    total = response.pagination.total;
    page += 1;
  } while (all.length < total);
  return all;
}

export async function fetchFacultyAffiliations(facultyId: number) {
  return apiGet<{
    faculty_id: number;
    faculty_name: string;
    items: Array<{ id: number; name: string; url: string; category: string }>;
  }>(`/publications/faculty/${facultyId}/affiliations`);
}

export async function deletePublication(publicationId: number): Promise<void> {
  await apiDelete(`/publications/publications/${publicationId}`);
}

export async function syncAllPublications(): Promise<{ status: string; message: string }> {
  return apiPostJson("/publications/scrape/sync-all", {});
}

export async function backfillPublicationDates(): Promise<{ status: string; message: string }> {
  return apiPostJson("/publications/scrape/backfill-dates", {});
}

export async function listCustomColumns(): Promise<CustomColumn[]> {
  return apiGet("/publications/custom-columns");
}

export async function createCustomColumn(body: CustomColumnInput): Promise<CustomColumn> {
  return apiPostJson("/publications/custom-columns", body);
}

export async function updateCustomColumn(
  id: number,
  body: Partial<CustomColumnInput> & { enabled?: boolean }
): Promise<CustomColumn> {
  return apiPatchJson(`/publications/custom-columns/${id}`, body);
}

export async function deleteCustomColumn(id: number): Promise<void> {
  await apiDelete(`/publications/custom-columns/${id}`);
}

export async function suggestCustomColumnSources(
  label: string,
  description?: string
): Promise<{ label: string; source_keys: string; crossref_field: string | null; note: string }> {
  return apiPostJson("/publications/custom-columns/suggest", { label, description });
}

export async function backfillCustomColumns(): Promise<{ status: string; message: string }> {
  return apiPostJson("/publications/custom-columns/backfill", {});
}

export async function getScrapeLogs(params?: {
  page?: number;
  page_size?: number;
}): Promise<{ items: ScrapeLogEntry[]; pagination: PaginationMeta }> {
  const qs = new URLSearchParams();
  if (params?.page) qs.set("page", String(params.page));
  if (params?.page_size) qs.set("page_size", String(params.page_size));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiGet(`/publications/scrape/logs${suffix}`);
}
