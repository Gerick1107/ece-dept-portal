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
  semesters: string;
  faculty_id: number;
  faculty_name: string;
  co_guide: string | null;
  course_code: string | null;
  course_name: string | null;
  student_roll_nos: string;
  student_names: string;
  credit: number | null;
  students: string[];
  student_rolls: string[];
  sdg_review_status: string;
  suggested_sdgs: SdgBrief[];
  confirmed_sdgs: SdgBrief[];
  upload_batch_id: number | null;
};

export type ProjectFilterOptions = {
  semesters: string[];
  course_codes: string[];
  course_names: string[];
  guides: { id: number; name: string }[];
  co_guides: string[];
  project_types: string[];
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
  merged?: number;
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

export type CourseRecord = {
  id: number;
  course_code: string;
  course_name: string;
  label: string;
};

export type FacultyAward = {
  id: number;
  faculty_name: string;
  year: string;
  exact_year?: number | null;
  awarded_by?: string | null;
  award: string;
  created_at?: string | null;
  updated_at?: string | null;
};

export type FacultyFdp = {
  id: number;
  faculty_name: string;
  year: string;
  exact_year?: number | null;
  program: string;
  description: string;
  no_of_days?: number | null;
  no_of_attendees?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type FdpsListResponse = {
  items: FacultyFdp[];
  years: string[];
  exact_years: number[];
  faculty_names: string[];
};

export type AwardsListResponse = {
  items: FacultyAward[];
  years: string[];
  exact_years: number[];
  faculty_names: string[];
};
