export type SdgBrief = {
  id: number;
  sdg_number: number;
  sdg_name: string;
  is_confirmed: boolean;
  confidence_score?: number | null;
};

export type Project = {
  id: number;
  project_title: string;
  project_type: string;
  semester: string;
  faculty_id: number;
  faculty_name: string;
  co_guide: string | null;
  status: string;
  credit: string | null;
  students: string[];
  sdg_review_status: string;
  suggested_sdgs: SdgBrief[];
  confirmed_sdgs: SdgBrief[];
  upload_batch_id: number | null;
};

export type ProjectListResponse = {
  items: Project[];
  pagination: { page: number; page_size: number; total: number };
};

export type SdgCatalogItem = {
  id: number;
  sdg_number: number;
  sdg_name: string;
  description: string | null;
};

export type ImportSummary = {
  upload_id: number;
  imported: number;
  total_rows?: number;
  skipped_rows?: number;
  sdg_queued?: number;
  errors: string[];
};

export type ProjectUploadRow = {
  id: number;
  filename: string;
  filepath: string;
  uploaded_by: number | null;
  uploaded_at: string | null;
  record_count: number;
};
