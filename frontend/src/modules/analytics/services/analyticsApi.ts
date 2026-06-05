import { apiGet } from "../../../services/api";

const CACHE_MS = 5 * 60 * 1000;
const cache = new Map<string, { at: number; data: unknown }>();

async function cachedGet<T>(key: string, path: string): Promise<T> {
  const hit = cache.get(key);
  if (hit && Date.now() - hit.at < CACHE_MS) {
    return hit.data as T;
  }
  const res = await apiGet<{ success: boolean; data: T }>(path);
  cache.set(key, { at: Date.now(), data: res.data });
  return res.data;
}

export function invalidateAnalyticsCache() {
  cache.clear();
}

export function fetchCopoAnalytics(params: Record<string, string | undefined> = {}) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) p.set(k, v);
  });
  const qs = p.toString();
  return cachedGet<CopoAnalyticsData>(`copo:${qs}`, `/analytics/copo${qs ? `?${qs}` : ""}`);
}

export function fetchProjectsAnalytics(params: Record<string, string | undefined> = {}) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) p.set(k, v);
  });
  const qs = p.toString();
  return cachedGet<ProjectsAnalyticsData>(`projects:${qs}`, `/analytics/projects${qs ? `?${qs}` : ""}`);
}

export function fetchAwardsAnalytics(params: Record<string, string | undefined> = {}) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) p.set(k, v);
  });
  const qs = p.toString();
  return cachedGet<AwardsAnalyticsData>(`awards:${qs}`, `/analytics/awards${qs ? `?${qs}` : ""}`);
}

export function fetchPublicationsAnalytics(params: Record<string, string | undefined> = {}) {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v) p.set(k, v);
  });
  const qs = p.toString();
  return cachedGet<PublicationsAnalyticsData>(`pubs:${qs}`, `/analytics/publications${qs ? `?${qs}` : ""}`);
}

export type CopoRun = {
  public_id: string;
  course_title: string;
  semester_label: string;
  run_key?: string;
  run_created_at: string | null;
  co_attainment: Record<string, number>;
  po_attainment: Record<string, number>;
  co_po_mapping: Record<string, Record<string, number>>;
  unique_cos: string[];
};

export type CopoAnalyticsData = {
  kpis: {
    total_courses: number;
    total_runs: number;
    avg_co_attainment: number | null;
    avg_po_attainment: number | null;
  };
  course_titles: string[];
  courses: Array<{ course_title: string; runs: CopoRun[]; latest_run: CopoRun | null }>;
};

export type ProjectsAnalyticsData = {
  kpis: {
    total_projects: number;
    unique_students: number;
    unique_guides: number;
    with_co_guide: number;
    thesis_count: number;
    ip_is_ur_count: number;
  };
  semester_chart: Array<{ semester: string; thesis: number; ip_is_ur: number; total: number }>;
  course_code_distribution: Array<{ course_code: string; count: number }>;
  faculty_load: Array<{ faculty_name: string; as_guide: number; as_co_guide: number; total: number }>;
  specialization_distribution: Array<{ name: string; count: number }>;
  sdg_review_status: Array<{ status: string; count: number }>;
  top_keywords: Array<{ keyword: string; count: number }>;
  filter_options: { semesters: string[]; faculty: Array<{ id: number; name: string }>; course_codes: string[] };
};

export type AwardsAnalyticsData = {
  kpis: {
    total_awards: number;
    faculty_with_awards: number;
    top_faculty: { name: string; count: number } | null;
    top_year: { year: string; count: number } | null;
    top_category: { category: string; count: number } | null;
  };
  faculty_chart: Array<{ faculty_name: string; total: number; by_category: Record<string, number> }>;
  year_chart: Array<{ year: string; total: number; cumulative: number; by_category: Record<string, number> }>;
  category_distribution: Array<{ category: string; count: number }>;
  heatmap: {
    faculty_names: string[];
    years: string[];
    cells: Array<{ faculty_name: string; year: string; count: number }>;
  };
  filter_options: { faculty_names: string[]; years: string[]; categories: string[] };
};

export type PublicationsAnalyticsData = {
  kpis: {
    total_publications: number;
    total_patents: number;
    total_citations: number;
    iiitd_publications: number;
    avg_citations: number;
  };
  is_empty: boolean;
  year_chart: Array<{ year: number; journal: number; conference: number; book: number; patent: number; total: number }>;
  type_distribution: Array<{ type: string; count: number }>;
  top_venues: {
    conference: Array<{ name: string; count: number }>;
    journal: Array<{ name: string; count: number }>;
    publisher: Array<{ name: string; count: number }>;
  };
  citation_distribution: Array<{ bucket: string; count: number }>;
  iiitd_split: { iiitd: number; external: number };
  top_cited: Array<{ title: string; authors: string | null; year: number | null; venue: string; citations: number }>;
};
