import type { ReactNode } from "react";

export type ContributionResource =
  | "memberships"
  | "resource-person-events"
  | "mooc-development"
  | "department-fdp-events"
  | "student-project-support"
  | "collaborations"
  | "faculty-services"
  | "phd-students";

export type ColumnDef = {
  key: string;
  label: string;
  render?: (row: Record<string, unknown>) => ReactNode;
};

export type FormField = {
  key: string;
  label: string;
  type: "text" | "number" | "textarea";
  required?: boolean;
};

export type TabConfig = {
  resource: ContributionResource;
  label: string;
  addLabel: string;
  searchPlaceholder: string;
  showYearFilters: boolean;
  showExactYearFilter: boolean;
  showExtraFilter?: { label: string; allLabel: string; values?: string[] };
  noDateNote?: string;
  recordLabel: string;
  columns: ColumnDef[];
  formFields: FormField[];
};

export const CONTRIBUTION_TABS: TabConfig[] = [
  {
    resource: "resource-person-events",
    label: "Resource Person (STTP/FDP)",
    addLabel: "Add Event",
    searchPlaceholder: "Search faculty, program, organizer, location…",
    showYearFilters: true,
    showExactYearFilter: true,
    recordLabel: "events",
    columns: [
      { key: "year", label: "Academic Year", render: (r) => String(r.exact_year ?? r.year ?? "—") },
      { key: "program_name", label: "Program/Event" },
      { key: "event_date", label: "Date" },
      { key: "location", label: "Location" },
      { key: "organized_by", label: "Organized By" },
    ],
    formFields: [
      { key: "year", label: "Academic year", type: "text", required: true },
      { key: "exact_year", label: "Year", type: "number" },
      { key: "program_name", label: "Program/Event", type: "text", required: true },
      { key: "event_date", label: "Date", type: "text", required: true },
      { key: "location", label: "Location", type: "text", required: true },
      { key: "organized_by", label: "Organized By", type: "text", required: true },
    ],
  },
  {
    resource: "mooc-development",
    label: "MOOC / SWAYAM Development",
    addLabel: "Add Course",
    searchPlaceholder: "Search faculty, course, platform, remarks…",
    showYearFilters: false,
    showExactYearFilter: false,
    noDateNote: "This dataset does not track dates — showing all records.",
    showExtraFilter: { label: "Platform", allLabel: "All platforms", values: ["NPTEL Swayam", "Other"] },
    recordLabel: "courses",
    columns: [
      { key: "course_name", label: "Course" },
      { key: "platform", label: "Platform" },
      { key: "remarks", label: "Remarks" },
    ],
    formFields: [
      { key: "course_name", label: "Course name", type: "text", required: true },
      { key: "platform", label: "Platform", type: "text", required: true },
      { key: "remarks", label: "Remarks", type: "textarea" },
    ],
  },
  {
    resource: "department-fdp-events",
    label: "Dept. Organized FDPs/STPs",
    addLabel: "Add Event",
    searchPlaceholder: "Search faculty, program, co-speakers…",
    showYearFilters: true,
    showExactYearFilter: true,
    recordLabel: "events",
    columns: [
      { key: "year", label: "Academic Year", render: (r) => String(r.exact_year ?? r.year ?? "—") },
      { key: "program_name", label: "Program" },
      { key: "event_date", label: "Date" },
      { key: "duration", label: "Duration" },
      { key: "co_speakers", label: "Co-Speakers" },
      { key: "no_of_attendees", label: "Attendees" },
    ],
    formFields: [
      { key: "year", label: "Academic year", type: "text", required: true },
      { key: "exact_year", label: "Year", type: "number" },
      { key: "program_name", label: "Program", type: "text", required: true },
      { key: "event_date", label: "Date", type: "text", required: true },
      { key: "duration", label: "Duration", type: "text", required: true },
      { key: "speaker_affiliation", label: "Speaker affiliation", type: "text" },
      { key: "co_speakers", label: "Co-speakers", type: "textarea" },
      { key: "no_of_attendees", label: "Attendees", type: "number" },
    ],
  },
  {
    resource: "student-project-support",
    label: "Student Project Support",
    addLabel: "Add Record",
    searchPlaceholder: "Search faculty, event, place…",
    showYearFilters: true,
    showExactYearFilter: true,
    recordLabel: "records",
    columns: [
      { key: "year", label: "Academic Year", render: (r) => String(r.exact_year ?? r.year ?? "—") },
      { key: "event_name", label: "Event" },
      { key: "event_date", label: "Date" },
      { key: "place", label: "Place" },
      {
        key: "website_link",
        label: "Link",
        render: (r) =>
          r.website_link ? (
            <a href={String(r.website_link)} target="_blank" rel="noreferrer" className="text-teal-700 underline">
              ↗
            </a>
          ) : (
            "—"
          ),
      },
    ],
    formFields: [
      { key: "year", label: "Academic year", type: "text", required: true },
      { key: "exact_year", label: "Year", type: "number" },
      { key: "event_name", label: "Event", type: "text", required: true },
      { key: "event_date", label: "Date", type: "text", required: true },
      { key: "place", label: "Place", type: "text", required: true },
      { key: "website_link", label: "Website link", type: "text" },
    ],
  },
  {
    resource: "collaborations",
    label: "Internships / Collaborations",
    addLabel: "Add Record",
    searchPlaceholder: "Search faculty, type, company, outcomes…",
    showYearFilters: false,
    showExactYearFilter: false,
    noDateNote: "This dataset does not track dates — showing all records.",
    showExtraFilter: { label: "Collaboration type", allLabel: "All types" },
    recordLabel: "records",
    columns: [
      { key: "collaboration_type", label: "Type" },
      { key: "company_place", label: "Company/Place" },
      { key: "duration", label: "Duration" },
      { key: "outcomes", label: "Outcomes" },
    ],
    formFields: [
      { key: "collaboration_type", label: "Type", type: "text", required: true },
      { key: "company_place", label: "Company/Place", type: "text", required: true },
      { key: "duration", label: "Duration", type: "text", required: true },
      { key: "outcomes", label: "Outcomes", type: "textarea", required: true },
    ],
  },
  {
    resource: "memberships",
    label: "Professional Memberships",
    addLabel: "Add Membership",
    searchPlaceholder: "Search faculty, society, grade…",
    showYearFilters: false,
    showExactYearFilter: false,
    noDateNote: "This dataset does not track dates — showing all records.",
    recordLabel: "memberships",
    columns: [
      { key: "society_name", label: "Society/Body" },
      { key: "grade_position", label: "Grade/Position" },
    ],
    formFields: [
      { key: "society_name", label: "Society/Body", type: "text", required: true },
      { key: "grade_position", label: "Grade/Position", type: "text", required: true },
    ],
  },
  {
    resource: "faculty-services",
    label: "Faculty Services",
    addLabel: "Add Service",
    searchPlaceholder: "Search faculty, role, organization…",
    showYearFilters: true,
    showExactYearFilter: true,
    showExtraFilter: { label: "Scope", allLabel: "All scopes", values: ["Institute", "External"] },
    recordLabel: "service records",
    columns: [
      { key: "scope", label: "Scope" },
      { key: "role_title", label: "Role/Title" },
      { key: "organization", label: "Organization" },
      {
        key: "duration_text",
        label: "Duration",
        render: (r) => {
          const start = r.start_date ? String(r.start_date) : "";
          const end = r.end_date ? String(r.end_date) : "";
          if (start || end) return `${start || "—"} – ${end || "—"}`;
          return String(r.duration_text ?? "—");
        },
      },
      { key: "description", label: "Description" },
    ],
    formFields: [
      { key: "year", label: "Academic year", type: "text" },
      { key: "exact_year", label: "Year", type: "number" },
      { key: "scope", label: "Scope (Institute/External)", type: "text", required: true },
      { key: "role_title", label: "Role/Title", type: "text", required: true },
      { key: "organization", label: "Organization", type: "text" },
      { key: "start_date", label: "Start date", type: "text" },
      { key: "end_date", label: "End date", type: "text" },
      { key: "duration_text", label: "Duration text", type: "text" },
      { key: "description", label: "Description", type: "textarea" },
    ],
  },
  {
    resource: "phd-students",
    label: "PhD Students",
    addLabel: "Add Snapshot",
    searchPlaceholder: "Search faculty…",
    showYearFilters: false,
    showExactYearFilter: true,
    recordLabel: "snapshots",
    columns: [
      { key: "students_graduated", label: "Students Graduated" },
      { key: "ongoing_phd_students", label: "Ongoing PhD Students" },
      { key: "as_of_year", label: "As of Year" },
    ],
    formFields: [
      { key: "as_of_year", label: "As of year", type: "number", required: true },
      { key: "students_graduated", label: "Students graduated", type: "number", required: true },
      { key: "ongoing_phd_students", label: "Ongoing PhD students", type: "number", required: true },
    ],
  },
];
