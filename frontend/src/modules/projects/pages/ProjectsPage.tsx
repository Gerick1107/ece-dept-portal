import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import {
  acceptSdgs,
  bulkAcceptSdgs,
  createProject,
  deleteProject,
  downloadImportTemplate,
  downloadProjectExport,
  editSdgs,
  generateSdgs,
  getProjectFilters,
  getProjectSettings,
  importProjects,
  listProjects,
  listSdgCatalog,
  previewBulkAcceptSdgs,
  purgeAllProjects,
  rejectSdgs,
  updateProject,
  type BulkSdgPreview,
} from "../services/projectsApi";
import type { ImportSummary, Project, ProjectFilterOptions, SdgCatalogItem } from "../types/projects";

const SDG_THRESHOLD = 0.5;
const SDG_TABLE_MAX = 3;

function effectiveSdgStatus(project: Project): string {
  if (project.sdg_review_status === "none" && project.suggested_sdgs.length > 0) {
    return "pending_review";
  }
  return project.sdg_review_status;
}

function showRegenerateButton(project: Project, llmEnabled: boolean): boolean {
  if (!llmEnabled) return false;
  const status = effectiveSdgStatus(project);
  return status === "none" || status === "rejected";
}

function sdgTableLine(s: { sdg_number: number; confidence_score?: number | null }) {
  const pct = s.confidence_score != null ? ` (${Math.round(s.confidence_score * 100)}%)` : "";
  return `SDG ${s.sdg_number}${pct}`;
}

function SdgTableCell({ project, onReview }: { project: Project; onReview: () => void }) {
  const status = effectiveSdgStatus(project);

  const renderLines = (lines: string[]) => {
    const visible = lines.slice(0, SDG_TABLE_MAX);
    const more = lines.length - SDG_TABLE_MAX;
    return (
      <div className="flex flex-col gap-0.5 text-xs leading-snug">
        {visible.map((line) => (
          <span key={line}>{line}</span>
        ))}
        {more > 0 && (
          <button type="button" className="text-teal-700 text-left hover:underline" onClick={onReview}>
            +{more} more
          </button>
        )}
      </div>
    );
  };

  if (status === "rejected") {
    return <span className="text-xs italic text-slate-400">No SDGs assigned</span>;
  }

  if (status === "confirmed") {
    if (!project.confirmed_sdgs.length) {
      return <span className="text-xs italic text-slate-400">No SDGs assigned</span>;
    }
    return renderLines(project.confirmed_sdgs.map(sdgTableLine));
  }

  const filtered = project.suggested_sdgs.filter(
    (s) => s.confidence_score != null && s.confidence_score >= SDG_THRESHOLD
  );
  if (!filtered.length) {
    return <span className="text-xs italic text-slate-400">No SDGs assigned</span>;
  }

  return renderLines(filtered.map(sdgTableLine));
}

function CommaCell({ value }: { value: string | null | undefined }) {
  const items = (value ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (!items.length) return <>—</>;
  return (
    <div className="flex flex-col gap-0.5 text-xs leading-snug max-w-[12rem]">
      {items.map((item) => (
        <span key={item}>{item}</span>
      ))}
    </div>
  );
}

const SEMESTER_TERMS = ["Monsoon", "Winter", "Summer"] as const;

import EceEveProjectsTab from "./EceEveProjectsTab";

const PROJECT_TABS = [
  { id: "btp", label: "Projects and Theses" },
  { id: "ece_eve", label: "ECE/EVE Projects" },
] as const;

type ProjectTabId = (typeof PROJECT_TABS)[number]["id"];

export default function ProjectsPage() {
  const [projectTab, setProjectTab] = useState<ProjectTabId>("btp");
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const isFaculty = user?.role === "faculty" || user?.role === "hod";
  const canReviewSdgs = isAdmin || isFaculty;
  const canImport = isAdmin || isFaculty;

  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [filterOptions, setFilterOptions] = useState<ProjectFilterOptions | null>(null);
  const [sdgCatalog, setSdgCatalog] = useState<SdgCatalogItem[]>([]);
  const [llmEnabled, setLlmEnabled] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [reviewProject, setReviewProject] = useState<Project | null>(null);
  const [editSdgsSelection, setEditSdgsSelection] = useState<number[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showBulkSdgModal, setShowBulkSdgModal] = useState(false);
  const [bulkGuideId, setBulkGuideId] = useState("");
  const [bulkFromSemester, setBulkFromSemester] = useState("");
  const [bulkToSemester, setBulkToSemester] = useState("");
  const [bulkPreview, setBulkPreview] = useState<BulkSdgPreview | null>(null);
  const [bulkPreviewBusy, setBulkPreviewBusy] = useState(false);
  const [importSummary, setImportSummary] = useState<ImportSummary | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [importSemester, setImportSemester] = useState<(typeof SEMESTER_TERMS)[number]>("Monsoon");
  const [importYear, setImportYear] = useState(String(new Date().getFullYear()));

  const [filters, setFilters] = useState({
    query: "",
    faculty_id: "",
    project_type: "",
    semesters: [] as string[],
    course_codes: [] as string[],
    course_name: "",
    co_guide: "",
    credit: "",
    page: 1,
  });

  const [form, setForm] = useState({
    project_title: "",
    project_type: "Thesis",
    semesters: "",
    faculty_id: "",
    co_guide: "",
    course_code: "",
    course_name: "",
    credit: "",
    student_roll_nos: "",
    student_names: "",
  });

  const apiFilters = useMemo(
    () => ({
      page: filters.page,
      page_size: 50,
      query: filters.query || undefined,
      faculty_id: filters.faculty_id ? Number(filters.faculty_id) : undefined,
      project_type: filters.project_type || undefined,
      semesters: filters.semesters.length ? filters.semesters.join(",") : undefined,
      course_codes: filters.course_codes.length ? filters.course_codes.join(",") : undefined,
      course_name: filters.course_name || undefined,
      co_guide: filters.co_guide || undefined,
      credit: filters.credit || undefined,
      confirmed_sdg_only: false,
    }),
    [filters]
  );

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await listProjects(apiFilters);
      setProjects(r.items);
      setTotal(r.pagination.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projects");
    }
  }, [apiFilters]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    getProjectFilters().then(setFilterOptions).catch(() => {});
    listSdgCatalog().then(setSdgCatalog).catch(() => {});
    getProjectSettings()
      .then((s) => setLlmEnabled(s.enable_sdg_llm))
      .catch(() => setLlmEnabled(false));
  }, []);

  function validateImportFile(file: File): string | null {
    const name = file.name.toLowerCase();
    if (!/\.(xlsx|xls|csv)$/.test(name)) {
      return "Only .xlsx, .xls, or .csv files are accepted (not .zip or other formats).";
    }
    return null;
  }

  async function runImport(file: File) {
    const fileError = validateImportFile(file);
    if (fileError) {
      setError(fileError);
      return;
    }
    const semesterTag = `${importSemester} ${importYear}`.trim();
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const r = await importProjects(file, semesterTag);
      setImportSummary(r);
      setShowImportModal(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  function openCreate() {
    setEditing(null);
    setForm({
      project_title: "",
      project_type: "Thesis",
      semesters: "",
      faculty_id: "",
      co_guide: "",
      course_code: "",
      course_name: "",
      credit: "",
      student_roll_nos: "",
      student_names: "",
    });
    setShowForm(true);
  }

  function openEdit(p: Project) {
    setEditing(p);
    setForm({
      project_title: p.project_title,
      project_type: p.project_type,
      semesters: p.semesters,
      faculty_id: String(p.faculty_id),
      co_guide: p.co_guide ?? "",
      course_code: p.course_code ?? "",
      course_name: p.course_name ?? "",
      credit: p.credit != null ? String(p.credit) : "",
      student_roll_nos: p.student_roll_nos,
      student_names: p.student_names,
    });
    setShowForm(true);
  }

  async function saveForm() {
    setBusy(true);
    const body = {
      project_title: form.project_title,
      project_type: form.project_type,
      semesters: form.semesters,
      faculty_id: Number(form.faculty_id),
      co_guide: form.co_guide || null,
      course_code: form.course_code || null,
      course_name: form.course_name || null,
      credit: form.credit ? Number(form.credit) : null,
      student_roll_nos: form.student_roll_nos,
      student_names: form.student_names,
    };
    try {
      if (editing) {
        await updateProject(editing.id, body);
        setMessage("Project updated.");
      } else {
        await createProject(body);
        setMessage("Project created.");
      }
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async function openSdgReview(p: Project) {
    setReviewProject(p);
    const nums =
      p.confirmed_sdgs.length > 0
        ? p.confirmed_sdgs.map((s) => s.sdg_number)
        : p.suggested_sdgs.filter((s) => (s.confidence_score ?? 0) >= SDG_THRESHOLD).map((s) => s.sdg_number);
    setEditSdgsSelection(nums);
  }

  function toggleSemesterFilter(tag: string) {
    setFilters((prev) => {
      const exists = prev.semesters.includes(tag);
      return {
        ...prev,
        page: 1,
        semesters: exists ? prev.semesters.filter((s) => s !== tag) : [...prev.semesters, tag],
      };
    });
  }

  function toggleCourseCodeFilter(code: string) {
    setFilters((prev) => {
      const exists = prev.course_codes.includes(code);
      return {
        ...prev,
        page: 1,
        course_codes: exists ? prev.course_codes.filter((c) => c !== code) : [...prev.course_codes, code],
      };
    });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-1 border-b border-slate-200 pb-1">
        {PROJECT_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setProjectTab(t.id)}
            className={`px-4 py-2 text-sm rounded-t-lg transition-colors ${
              projectTab === t.id
                ? "bg-white border border-b-white border-slate-200 font-medium text-teal-800 -mb-px"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {projectTab === "ece_eve" ? (
        <EceEveProjectsTab />
      ) : (
        <>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Projects and Theses Repository</h2>
          <p className="text-sm text-slate-600 mt-1">
            Import department Excel sheets, filter ECE projects, and manage SDG tags.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => downloadImportTemplate()}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
          >
            Download template
          </button>
          {canReviewSdgs && (
            <button
              type="button"
              onClick={() => {
                setError("");
                setBulkPreview(null);
                setShowBulkSdgModal(true);
              }}
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
            >
              Bulk accept SDGs
            </button>
          )}
          {canImport && (
            <button
              type="button"
              onClick={() => {
                setError("");
                setShowImportModal(true);
              }}
              className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm hover:bg-teal-800"
            >
              Import Excel
            </button>
          )}
          {isAdmin && (
            <>
              <button
                type="button"
                className="rounded-lg border border-red-300 text-red-800 px-3 py-2 text-sm hover:bg-red-50"
                disabled={busy}
                onClick={async () => {
                  if (!window.confirm("Delete ALL Projects and Theses entries? This cannot be undone.")) return;
                  setBusy(true);
                  try {
                    const r = await purgeAllProjects();
                    setMessage(`Purged all project data (${r.removed_files} files removed).`);
                    await load();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Purge failed");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Purge all
              </button>
              <button type="button" onClick={openCreate} className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm">
                Add project
              </button>
            </>
          )}
        </div>
      </div>

      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2 whitespace-pre-wrap">{error}</p>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <h3 className="text-sm font-semibold text-slate-700">Search & filters</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <input
            placeholder="Search title, guide, students…"
            className="border rounded-lg px-3 py-2 text-sm sm:col-span-2"
            value={filters.query}
            onChange={(e) => setFilters({ ...filters, query: e.target.value, page: 1 })}
          />
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.faculty_id}
            onChange={(e) => setFilters({ ...filters, faculty_id: e.target.value, page: 1 })}
          >
            <option value="">Guide (all ECE)</option>
            {filterOptions?.guides.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.project_type}
            onChange={(e) => setFilters({ ...filters, project_type: e.target.value, page: 1 })}
          >
            <option value="">Project type (all)</option>
            {(filterOptions?.project_types ?? ["Thesis", "IP/IS/UR"]).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.course_name}
            onChange={(e) => setFilters({ ...filters, course_name: e.target.value, page: 1 })}
          >
            <option value="">Course name (all)</option>
            {filterOptions?.course_names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.co_guide}
            onChange={(e) => setFilters({ ...filters, co_guide: e.target.value, page: 1 })}
          >
            <option value="">Co-Guide (all)</option>
            {filterOptions?.co_guides.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
          <input
            placeholder="Credit"
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.credit}
            onChange={(e) => setFilters({ ...filters, credit: e.target.value, page: 1 })}
          />
        </div>
        {filterOptions && filterOptions.semesters.length > 0 && (
          <div>
            <p className="text-xs text-slate-500 mb-1">Semester (multi-select)</p>
            <div className="flex flex-wrap gap-2">
              {filterOptions.semesters.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleSemesterFilter(tag)}
                  className={`text-xs px-2 py-1 rounded-full border ${
                    filters.semesters.includes(tag)
                      ? "bg-teal-700 text-white border-teal-700"
                      : "bg-white text-slate-700 border-slate-300"
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        )}
        {filterOptions && filterOptions.course_codes.length > 0 && (
          <div>
            <p className="text-xs text-slate-500 mb-1">Course code (multi-select)</p>
            <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
              {filterOptions.course_codes.map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => toggleCourseCodeFilter(code)}
                  className={`text-xs px-2 py-1 rounded-full border ${
                    filters.course_codes.includes(code)
                      ? "bg-teal-700 text-white border-teal-700"
                      : "bg-white text-slate-700 border-slate-300"
                  }`}
                >
                  {code}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => load()} className="rounded-lg bg-slate-800 text-white px-3 py-1.5 text-sm">
            Apply
          </button>
          <button
            type="button"
            onClick={() =>
              downloadProjectExport(apiFilters, "xlsx").catch((e) =>
                setError(e instanceof Error ? e.message : "Export failed")
              )
            }
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
          >
            Export XLSX
          </button>
        </div>
      </section>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
          <table className="w-full text-sm border-collapse min-w-[1600px]">
            <thead className="sticky top-0 z-10 bg-slate-50 shadow-sm">
              <tr className="text-slate-600 text-left">
                <th className="px-3 py-2 font-medium whitespace-nowrap">Serial Number</th>
                <th className="px-3 py-2 font-medium min-w-[9rem]">Semester</th>
                <th className="px-3 py-2 font-medium min-w-[14rem]">Title</th>
                <th className="px-3 py-2 font-medium whitespace-nowrap">Course Code</th>
                <th className="px-3 py-2 font-medium min-w-[8rem]">Course Name</th>
                <th className="px-3 py-2 font-medium min-w-[8rem]">Guide</th>
                <th className="px-3 py-2 font-medium min-w-[8rem]">Co-Guide</th>
                <th className="px-3 py-2 font-medium min-w-[9rem]">Student Roll Number</th>
                <th className="px-3 py-2 font-medium min-w-[9rem]">Student Name</th>
                <th className="px-3 py-2 font-medium min-w-[14rem]">SDGs</th>
                <th className="px-3 py-2 font-medium whitespace-nowrap">Credit</th>
                {canReviewSdgs && <th className="px-3 py-2 font-medium min-w-[10rem]">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {projects.map((p, idx) => (
                <tr
                  key={p.id}
                  className={
                    p.sdg_ever_accepted || effectiveSdgStatus(p) === "confirmed"
                      ? "border-t border-teal-200/80 bg-teal-100/70 hover:bg-teal-100"
                      : "border-t border-slate-100 hover:bg-slate-50/80"
                  }
                >
                  <td className="px-3 py-2">{(filters.page - 1) * 50 + idx + 1}</td>
                  <td className="px-3 py-2">
                    <CommaCell value={p.semesters} />
                  </td>
                  <td className="px-3 py-2 font-medium text-slate-800 max-w-xs">{p.project_title}</td>
                  <td className="px-3 py-2">{p.course_code || "—"}</td>
                  <td className="px-3 py-2">{p.course_name || "—"}</td>
                  <td className="px-3 py-2">{p.faculty_name}</td>
                  <td className="px-3 py-2">{p.co_guide || "—"}</td>
                  <td className="px-3 py-2">
                    <CommaCell value={p.student_roll_nos} />
                  </td>
                  <td className="px-3 py-2">
                    <CommaCell value={p.student_names} />
                  </td>
                  <td className="px-3 py-2 align-top min-w-[14rem] max-w-[18rem]">
                    <SdgTableCell project={p} onReview={() => openSdgReview(p)} />
                  </td>
                  <td className="px-3 py-2">{p.credit ?? "—"}</td>
                  {canReviewSdgs && (
                    <td className="px-3 py-2 whitespace-nowrap">
                      <div className="flex flex-wrap items-center gap-2">
                        {isAdmin && (
                          <button type="button" className="text-xs px-2 py-1 rounded bg-slate-100" onClick={() => openEdit(p)}>
                            Edit
                          </button>
                        )}
                        <button type="button" className="text-xs px-2 py-1 rounded bg-teal-50 text-teal-800" onClick={() => openSdgReview(p)}>
                          {llmEnabled ? "Review SDGs" : "Edit SDGs"}
                        </button>
                        {showRegenerateButton(p, llmEnabled) && (
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded bg-amber-50 text-amber-800"
                            onClick={async () => {
                              try {
                                await generateSdgs(p.id);
                                await load();
                                setMessage("SDGs regenerated.");
                              } catch (e) {
                                setError(e instanceof Error ? e.message : "Regenerate failed");
                              }
                            }}
                          >
                            Regenerate
                          </button>
                        )}
                        {isAdmin && (
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded bg-red-50 text-red-700"
                            onClick={async () => {
                              if (!window.confirm("Delete this project?")) return;
                              await deleteProject(p.id);
                              await load();
                            }}
                          >
                            Delete
                          </button>
                        )}
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {!projects.length && (
                <tr>
                  <td colSpan={canReviewSdgs ? 12 : 11} className="px-3 py-8 text-center text-slate-500">
                    No projects match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-t text-xs text-slate-500">
          <span>
            Showing {(filters.page - 1) * 50 + 1}–{(filters.page - 1) * 50 + projects.length} of {total} projects
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={filters.page <= 1}
              onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
              className="rounded border border-slate-300 px-2 py-1 disabled:opacity-40"
            >
              Previous
            </button>
            <span>
              Page {filters.page} of {Math.max(1, Math.ceil(total / 50))}
            </span>
            <button
              type="button"
              disabled={filters.page >= Math.ceil(total / 50)}
              onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
              className="rounded border border-slate-300 px-2 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {showImportModal && canImport && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-4">
            <h3 className="font-semibold">Import projects</h3>
            <p className="text-sm text-slate-600">Select the semester for every row in this file. The Semester column in the Excel file is ignored.</p>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-500">Semester</label>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
                  value={importSemester}
                  onChange={(e) => setImportSemester(e.target.value as (typeof SEMESTER_TERMS)[number])}
                >
                  {SEMESTER_TERMS.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-500">Year</label>
                <input
                  type="number"
                  className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
                  value={importYear}
                  onChange={(e) => setImportYear(e.target.value)}
                />
              </div>
            </div>
            <p className="text-sm font-medium text-teal-800">
              Tag: {importSemester} {importYear}
            </p>
            <p className="text-xs text-slate-500">
              Upload the department Excel file (.xlsx or legacy .xls). Zip archives are not supported.
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) runImport(f);
                e.target.value = "";
              }}
            />
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowImportModal(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg"
                onClick={() => fileInputRef.current?.click()}
              >
                Choose file & import
              </button>
            </div>
          </div>
        </div>
      )}

      {importSummary && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3">
            <h3 className="font-semibold">Import summary</h3>
            <ul className="text-sm space-y-1 text-slate-700">
              <li>Total rows in file: {importSummary.total_rows ?? "—"}</li>
              <li>Rows imported to Projects and Theses: {importSummary.btp_imported ?? importSummary.imported}</li>
              <li>Rows added to ECE/EVE tab: {importSummary.ece_eve_imported ?? 0}</li>
              <li>Rows merged (existing projects): {importSummary.merged ?? 0}</li>
              <li>Rows skipped (non-ECE/EVE branch, no ECE faculty match): {importSummary.skipped_rows ?? 0}</li>
            </ul>
            {importSummary.errors.length > 0 && (
              <div className="text-xs text-red-700 bg-red-50 border border-red-200 rounded p-2 max-h-32 overflow-y-auto whitespace-pre-wrap">
                {importSummary.errors.join("\n")}
              </div>
            )}
            <button
              type="button"
              className="w-full px-3 py-2 text-sm bg-teal-700 text-white rounded-lg"
              onClick={() => setImportSummary(null)}
            >
              Close
            </button>
          </div>
        </div>
      )}

      {showForm && isAdmin && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-3 max-h-[90vh] overflow-y-auto">
            <h3 className="font-semibold">{editing ? "Edit project" : "Add project"}</h3>
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Title" value={form.project_title} onChange={(e) => setForm({ ...form, project_title: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Project type" value={form.project_type} onChange={(e) => setForm({ ...form, project_type: e.target.value })} />
              <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Semesters" value={form.semesters} onChange={(e) => setForm({ ...form, semesters: e.target.value })} />
            </div>
            <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.faculty_id} onChange={(e) => setForm({ ...form, faculty_id: e.target.value })}>
              <option value="">Select guide</option>
              {filterOptions?.guides.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Co-Guide" value={form.co_guide} onChange={(e) => setForm({ ...form, co_guide: e.target.value })} />
            <div className="grid grid-cols-2 gap-2">
              <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Course code" value={form.course_code} onChange={(e) => setForm({ ...form, course_code: e.target.value })} />
              <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Course name" value={form.course_name} onChange={(e) => setForm({ ...form, course_name: e.target.value })} />
            </div>
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Student roll nos (comma-separated)" value={form.student_roll_nos} onChange={(e) => setForm({ ...form, student_roll_nos: e.target.value })} />
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Student names (comma-separated)" value={form.student_names} onChange={(e) => setForm({ ...form, student_names: e.target.value })} />
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Credit" value={form.credit} onChange={(e) => setForm({ ...form, credit: e.target.value })} />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button type="button" disabled={busy} className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg" onClick={saveForm}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {reviewProject && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-3">
            <h3 className="font-semibold">{llmEnabled ? "SDG review" : "Edit SDGs"}</h3>
            <p className="text-sm text-slate-600">{reviewProject.project_title}</p>
            <p className="text-xs text-slate-500">
              All 17 SDGs are shown with model confidence. Items at or above 50% are auto-selected; you may override freely.
            </p>
            <div className="max-h-80 overflow-y-auto border rounded-lg divide-y divide-slate-100">
              {sdgCatalog.map((s) => {
                const scoreEntry =
                  reviewProject.confirmed_sdgs.find((x) => x.sdg_number === s.sdg_number) ??
                  reviewProject.suggested_sdgs.find((x) => x.sdg_number === s.sdg_number);
                const confidence = scoreEntry?.confidence_score;
                const pct = confidence != null ? Math.round(confidence * 100) : null;
                const aboveThreshold = confidence != null && confidence >= SDG_THRESHOLD;
                const isChecked = editSdgsSelection.includes(s.sdg_number);
                return (
                  <label
                    key={s.id}
                    data-selected={aboveThreshold ? "true" : "false"}
                    className={`flex items-center gap-2.5 px-2.5 py-1.5 text-sm cursor-pointer ${
                      aboveThreshold
                        ? "bg-sky-50 border-l-[3px] border-l-[#1a6fba] font-medium text-slate-800"
                        : "opacity-60 text-slate-600"
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="shrink-0"
                      checked={isChecked}
                      onChange={(e) => {
                        if (e.target.checked) setEditSdgsSelection([...editSdgsSelection, s.sdg_number]);
                        else setEditSdgsSelection(editSdgsSelection.filter((n) => n !== s.sdg_number));
                      }}
                    />
                    <span className="flex-1 min-w-0 truncate">
                      SDG {s.sdg_number}: {s.sdg_name}
                    </span>
                    <span className="min-w-[42px] text-right font-semibold tabular-nums shrink-0">
                      {pct != null ? `${pct}%` : "—"}
                    </span>
                  </label>
                );
              })}
            </div>
            <div className="flex flex-wrap gap-2">
              {llmEnabled ? (
                <>
                  <button
                    type="button"
                    className="text-sm bg-teal-700 text-white px-3 py-1.5 rounded-lg"
                    onClick={async () => {
                      try {
                        await acceptSdgs(reviewProject.id, editSdgsSelection);
                        setReviewProject(null);
                        setMessage("SDGs saved successfully.");
                        await load();
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Could not accept SDGs");
                      }
                    }}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    className="text-sm border px-3 py-1.5 rounded-lg"
                    onClick={async () => {
                      if (
                        !window.confirm(
                          "Are you sure you want to reject all SDGs for this project? This will clear all assigned SDGs."
                        )
                      ) {
                        return;
                      }
                      try {
                        await rejectSdgs(reviewProject.id);
                        setReviewProject(null);
                        setMessage("SDGs rejected. You can regenerate them if needed.");
                        await load();
                      } catch (e) {
                        setError(e instanceof Error ? e.message : "Could not reject SDGs");
                      }
                    }}
                  >
                    Reject
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="text-sm bg-teal-700 text-white px-3 py-1.5 rounded-lg"
                  onClick={async () => {
                    try {
                      await editSdgs(reviewProject.id, editSdgsSelection);
                      setReviewProject(null);
                      setMessage("SDGs saved successfully.");
                      await load();
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Could not save SDGs");
                    }
                  }}
                >
                  Save SDGs
                </button>
              )}
              <button type="button" className="text-sm ml-auto" onClick={() => setReviewProject(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {showBulkSdgModal && filterOptions && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-4">
            <h3 className="font-semibold">Bulk accept SDGs</h3>
            <p className="text-sm text-slate-600">
              Accept auto-suggested SDGs (≥50% confidence) for all pending-review projects where the selected
              faculty member is the <strong>primary guide</strong> and at least one semester falls in the range.
            </p>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-500">Guide (primary only)</label>
                <select
                  className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={bulkGuideId}
                  onChange={(e) => {
                    setBulkGuideId(e.target.value);
                    setBulkPreview(null);
                  }}
                >
                  <option value="">— Select guide —</option>
                  {filterOptions.guides.map((g) => (
                    <option key={g.id} value={String(g.id)}>
                      {g.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-500">From semester</label>
                  <select
                    className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                    value={bulkFromSemester}
                    onChange={(e) => {
                      setBulkFromSemester(e.target.value);
                      setBulkPreview(null);
                    }}
                  >
                    <option value="">—</option>
                    {filterOptions.semesters.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-xs text-slate-500">To semester</label>
                  <select
                    className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                    value={bulkToSemester}
                    onChange={(e) => {
                      setBulkToSemester(e.target.value);
                      setBulkPreview(null);
                    }}
                  >
                    <option value="">—</option>
                    {filterOptions.semesters.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            <button
              type="button"
              disabled={!bulkGuideId || !bulkFromSemester || !bulkToSemester || bulkPreviewBusy}
              className="text-sm border border-slate-300 rounded-lg px-3 py-2 hover:bg-slate-50 disabled:opacity-50"
              onClick={async () => {
                setBulkPreviewBusy(true);
                setError("");
                try {
                  const preview = await previewBulkAcceptSdgs({
                    faculty_id: Number(bulkGuideId),
                    from_semester: bulkFromSemester,
                    to_semester: bulkToSemester,
                  });
                  setBulkPreview(preview);
                } catch (e) {
                  setError(e instanceof Error ? e.message : "Preview failed");
                } finally {
                  setBulkPreviewBusy(false);
                }
              }}
            >
              {bulkPreviewBusy ? "Loading preview…" : "Preview matching projects"}
            </button>
            {bulkPreview && (
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-sm space-y-2 max-h-48 overflow-y-auto">
                <p>
                  <strong>{bulkPreview.count}</strong> project{bulkPreview.count === 1 ? "" : "s"} with pending SDGs
                  will be accepted.
                </p>
                {bulkPreview.projects.length > 0 && (
                  <ul className="text-xs text-slate-600 space-y-1">
                    {bulkPreview.projects.map((p) => (
                      <li key={p.id}>
                        {p.project_title} ({p.semesters.join(", ")}) — SDGs {p.sdg_numbers.join(", ")}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={!bulkPreview || bulkPreview.count === 0 || busy}
                className="text-sm bg-teal-700 text-white px-3 py-1.5 rounded-lg disabled:opacity-50"
                onClick={async () => {
                  if (
                    !window.confirm(
                      `Accept SDGs for ${bulkPreview?.count ?? 0} project(s)? Already-reviewed projects are skipped.`
                    )
                  ) {
                    return;
                  }
                  setBusy(true);
                  setError("");
                  try {
                    const result = await bulkAcceptSdgs({
                      faculty_id: Number(bulkGuideId),
                      from_semester: bulkFromSemester,
                      to_semester: bulkToSemester,
                    });
                    setShowBulkSdgModal(false);
                    setBulkPreview(null);
                    setMessage(
                      `Bulk accepted SDGs for ${result.accepted_count} project(s) on ${new Date(result.accepted_at).toLocaleString()}.`
                    );
                    await load();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Bulk accept failed");
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                Confirm bulk accept
              </button>
              <button
                type="button"
                className="text-sm ml-auto"
                onClick={() => {
                  setShowBulkSdgModal(false);
                  setBulkPreview(null);
                }}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
        </>
      )}
    </div>
  );
}
