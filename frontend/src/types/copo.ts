/** Shared CO-PO parse / scope types (counts only — no student identifiers). */

export type BranchInfo = {
  count: number;
  programme: string;
  branch: string;
};

export type MarksParsePreview = {
  cos: string[];
  programmes: Record<string, number>;
  branches: Record<string, BranchInfo>;
  total_students: number;
  upload_id: number;
  has_branch_data: boolean;
  default_programmes: string[];
  default_branches: string[];
  parse_message?: string;
};

export const PROGRAMME_LABELS: Record<string, string> = {
  UG: "UG (Undergraduate)",
  PG: "PG / M.Tech (MT prefix)",
  PhD: "PhD (PhD prefix)",
  Other: "Other",
};

export type ComparisonSetup = {
  input_sheet: string;
  compare_filename: string;
  mapping_filename: string;
  scope_summary: string;
  threshold_rule: string;
  delta_note?: string;
};
