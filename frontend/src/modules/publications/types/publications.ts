export type PaginationMeta = {
  page: number;
  page_size: number;
  total: number;
};

export type Faculty = {
  id: number;
  name: string;
  designation?: string | null;
  department?: string | null;
  scholar_id: string;
  join_year: number;
  leave_year?: number | null;
  photo_url?: string | null;
  profile_link?: string | null;
  total_citations: number;
  h_index: number;
  i10_index: number;
  is_active: boolean;
  total_publications: number;
};

export type Publication = {
  id: number;
  title: string;
  authors?: string | null;
  publication_year?: number | null;
  journal_or_conference?: string | null;
  citation_count: number;
  publication_type?: string | null;
  scholar_url?: string | null;
  source_hash: string;
  faculty_ids: number[];
};
