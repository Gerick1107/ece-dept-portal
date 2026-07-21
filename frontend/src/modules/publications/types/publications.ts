export type PaginationMeta = {
  page: number;
  page_size: number;
  total: number;
};

export type FacultyAffiliation = {
  id: number;
  name: string;
  url: string;
  category: string;
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
  publisher?: string | null;
  citation_count: number;
  link?: string | null;
  publication_date?: string | null;
  pages?: string | null;
  conference?: string | null;
  journal?: string | null;
  book?: string | null;
  volume?: string | null;
  issue?: string | null;
  is_patent: boolean;
  inventors?: string | null;
  patent_office?: string | null;
  patent_number?: string | null;
  application_number?: string | null;
  scholar_url?: string | null;
  source_hash: string;
  is_manual_book?: boolean;
  manual_overrides?: string[];
  faculty_ids: number[];
  custom_fields?: Record<string, string>;
};

export type PublicationTableMode = "publications" | "patents" | "all";

export type PublicationSearchBy = "title" | "venue";

export type PublicationEditPayload = {
  publisher?: string | null;
  publication_date?: string | null;
  pages?: string | null;
  conference?: string | null;
  journal?: string | null;
  book?: string | null;
  volume?: string | null;
  issue?: string | null;
  patent_office?: string | null;
  patent_number?: string | null;
  application_number?: string | null;
  is_manual_book?: boolean;
  custom_fields?: Record<string, string>;
};

export function publicationVenue(p: Publication): string {
  return p.journal || p.conference || p.book || "";
}

export function publicationTitleHref(p: Publication): string | null {
  return p.link || p.scholar_url || null;
}

export function publicationPeople(p: Publication): string {
  if (p.is_patent) {
    return p.inventors || p.authors || "";
  }
  return p.authors || "";
}

export function venueIsPreprintOrUnlisted(p: Publication): boolean {
  const journal = (p.journal || "").trim();
  const conference = (p.conference || "").trim();
  const book = (p.book || "").trim();
  if (!journal && !conference && !book) return true;
  const joined = `${journal} ${conference} ${book}`.toLowerCase();
  return joined.includes("arxiv");
}
