import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { listFaculty } from "../../publications/services/publicationsApi";
import type { Faculty } from "../../publications/types/publications";
import {
  acceptSdgs,
  createProject,
  deleteProject,
  downloadImportTemplate,
  downloadProjectExport,
  editSdgs,
  generateSdgs,
  getProjectSettings,
  importProjects,
  listProjects,
  listSdgCatalog,
  purgeAllProjects,
  rejectSdgs,
  updateProject,
} from "../services/projectsApi";
import type { Project, SdgCatalogItem } from "../types/projects";

function formatSdgs(project: Project) {
  if (project.confirmed_sdgs.length) {
    return project.confirmed_sdgs.map((s) => `SDG ${s.sdg_number}`).join(", ");
  }
  if (project.suggested_sdgs.length) {
    return project.suggested_sdgs
      .map((s) => `SDG ${s.sdg_number}${s.confidence_score != null ? ` (${Math.round(s.confidence_score * 100)}%)` : ""}`)
      .join(", ");
  }
  return "—";
}

export default function ProjectsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const isFaculty = user?.role === "faculty" || user?.role === "hod";
  const canReviewSdgs = isAdmin || isFaculty;
  const [projects, setProjects] = useState<Project[]>([]);
  const [total, setTotal] = useState(0);
  const [faculty, setFaculty] = useState<Faculty[]>([]);
  const [sdgCatalog, setSdgCatalog] = useState<SdgCatalogItem[]>([]);
  const [llmEnabled, setLlmEnabled] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [reviewProject, setReviewProject] = useState<Project | null>(null);
  const [editSdgsSelection, setEditSdgsSelection] = useState<number[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Project | null>(null);

  const [filters, setFilters] = useState({
    query: "",
    faculty_id: "",
    project_type: "",
    semester: "",
    student_name: "",
    sdg: "",
    status: "",
    credit: "",
    page: 1,
  });

  const [form, setForm] = useState({
    project_title: "",
    project_type: "BTP",
    semester: "",
    faculty_id: "",
    co_guide: "",
    status: "Pending",
    credit: "",
    students: "",
  });

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await listProjects({
        page: filters.page,
        page_size: 200,
        query: filters.query || undefined,
        faculty_id: filters.faculty_id ? Number(filters.faculty_id) : undefined,
        project_type: filters.project_type || undefined,
        semester: filters.semester || undefined,
        student_name: filters.student_name || undefined,
        sdg: filters.sdg ? Number(filters.sdg) : undefined,
        status: filters.status || undefined,
        credit: filters.credit || undefined,
        confirmed_sdg_only: false,
      });
      setProjects(r.items);
      setTotal(r.pagination.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load projects");
    }
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    listFaculty({ page: 1, page_size: 200, include_inactive: false })
      .then((r) => setFaculty(r.items))
      .catch(() => {});
    listSdgCatalog().then(setSdgCatalog).catch(() => {});
    getProjectSettings()
      .then((s) => setLlmEnabled(s.enable_sdg_llm))
      .catch(() => setLlmEnabled(false));
  }, []);

  async function handleImport(file: File) {
    setBusy(true);
    setMessage("");
    try {
      const r = await importProjects(file);
      const total = "total_rows" in r ? r.total_rows ?? "?" : "?";
      const queued = r.sdg_queued ?? 0;
      setMessage(
        `Imported ${r.imported} of ${total} rows.` +
          (queued && llmEnabled
            ? ` SDG tagging queued for ${queued} projects (runs in background).`
            : "") +
          (r.errors.length ? ` ${r.errors.length} import error(s) — see below.` : "")
      );
      if (r.errors.length) setError(r.errors.join("\n"));
      else setError("");
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
      project_type: "BTP",
      semester: "",
      faculty_id: "",
      co_guide: "",
      status: "Pending",
      credit: "",
      students: "",
    });
    setShowForm(true);
  }

  function openEdit(p: Project) {
    setEditing(p);
    setForm({
      project_title: p.project_title,
      project_type: p.project_type,
      semester: p.semester,
      faculty_id: String(p.faculty_id),
      co_guide: p.co_guide ?? "",
      status: p.status,
      credit: p.credit ?? "",
      students: p.students.join("; "),
    });
    setShowForm(true);
  }

  async function saveForm() {
    setBusy(true);
    const body = {
      project_title: form.project_title,
      project_type: form.project_type,
      semester: form.semester,
      faculty_id: Number(form.faculty_id),
      co_guide: form.co_guide || null,
      status: form.status,
      credit: form.credit || null,
      students: form.students.split(/[;,]/).map((s) => s.trim()).filter(Boolean),
    };
    try {
      if (editing) {
        await updateProject(editing.id, body);
        setMessage("Project updated.");
      } else {
        const created = await createProject(body);
        setMessage(
          created.suggested_sdgs?.length
            ? "Project created with AI-suggested SDGs (pending review)."
            : "Project created. SDG suggestions will appear when the API key is configured."
        );
      }
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  async   function openSdgReview(p: Project) {
    setReviewProject(p);
    const nums =
      p.confirmed_sdgs.length > 0
        ? p.confirmed_sdgs.map((s) => s.sdg_number)
        : p.suggested_sdgs.map((s) => s.sdg_number);
    setEditSdgsSelection(nums);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">BTP / IP Project Repository</h2>
          <p className="text-sm text-slate-600 mt-1">
            Manage projects, import spreadsheets
            {llmEnabled ? ", and review AI-suggested SDG tags" : ", and assign SDGs manually"}.
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
          {isAdmin && (
            <>
              <button
                type="button"
                className="rounded-lg border border-red-300 text-red-800 px-3 py-2 text-sm hover:bg-red-50"
                disabled={busy}
                onClick={async () => {
                  if (
                    !window.confirm(
                      "Delete ALL BTP/IP projects, SDG links, upload files, and database records? This cannot be undone."
                    )
                  ) {
                    return;
                  }
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
                Purge all projects
              </button>
              <label className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm cursor-pointer hover:bg-teal-800">
                Import Excel/CSV
                <input
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  className="hidden"
                  disabled={busy}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) handleImport(f);
                    e.target.value = "";
                  }}
                />
              </label>
              <button
                type="button"
                onClick={openCreate}
                className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm"
              >
                Add project
              </button>
            </>
          )}
        </div>
      </div>

      {isFaculty && (
        <p className="text-sm text-slate-600 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
          Faculty view: all department projects are visible. You can review SDGs on any project.
        </p>
      )}

      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2 whitespace-pre-wrap">{error}</p>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <h3 className="text-sm font-semibold text-slate-700">Search & filters</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <input
            placeholder="Project topic…"
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.query}
            onChange={(e) => setFilters({ ...filters, query: e.target.value, page: 1 })}
          />
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.faculty_id}
            onChange={(e) => setFilters({ ...filters, faculty_id: e.target.value, page: 1 })}
          >
            <option value="">All faculty</option>
            {faculty.map((f) => (
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
            <option value="">BTP & IP</option>
            <option value="BTP">BTP</option>
            <option value="IP">IP</option>
          </select>
          <input
            placeholder="Semester"
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.semester}
            onChange={(e) => setFilters({ ...filters, semester: e.target.value, page: 1 })}
          />
          <input
            placeholder="Student name"
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.student_name}
            onChange={(e) => setFilters({ ...filters, student_name: e.target.value, page: 1 })}
          />
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.sdg}
            onChange={(e) => setFilters({ ...filters, sdg: e.target.value, page: 1 })}
          >
            <option value="">Any SDG</option>
            {sdgCatalog.map((s) => (
              <option key={s.id} value={s.sdg_number}>
                SDG {s.sdg_number} — {s.sdg_name}
              </option>
            ))}
          </select>
          <input
            placeholder="Status"
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value, page: 1 })}
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => load()} className="rounded-lg bg-slate-800 text-white px-3 py-1.5 text-sm">
            Apply
          </button>
          {(["csv", "xlsx", "pdf"] as const).map((fmt) => (
            <button
              key={fmt}
              type="button"
              onClick={() =>
                downloadProjectExport(
                  {
                    query: filters.query || undefined,
                    faculty_id: filters.faculty_id ? Number(filters.faculty_id) : undefined,
                    project_type: filters.project_type || undefined,
                    semester: filters.semester || undefined,
                    student_name: filters.student_name || undefined,
                    sdg: filters.sdg ? Number(filters.sdg) : undefined,
                    status: filters.status || undefined,
                  },
                  fmt
                ).catch((e) => setError(e instanceof Error ? e.message : "Export failed"))
              }
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
            >
              Export {fmt.toUpperCase()}
            </button>
          ))}
        </div>
      </section>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse min-w-[1100px]">
            <thead>
              <tr className="bg-slate-50 text-slate-600 text-left">
                <th className="px-3 py-2 font-medium">Sl No</th>
                <th className="px-3 py-2 font-medium">Semester</th>
                <th className="px-3 py-2 font-medium">Project Topic</th>
                <th className="px-3 py-2 font-medium">Project Type</th>
                <th className="px-3 py-2 font-medium">Faculty</th>
                <th className="px-3 py-2 font-medium">Co Guide</th>
                <th className="px-3 py-2 font-medium">Students</th>
                <th className="px-3 py-2 font-medium">SDGs</th>
                <th className="px-3 py-2 font-medium">Status</th>
                <th className="px-3 py-2 font-medium">Credit</th>
                {canReviewSdgs && <th className="px-3 py-2 font-medium">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {projects.map((p, idx) => (
                <tr key={p.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                  <td className="px-3 py-2">{(filters.page - 1) * 200 + idx + 1}</td>
                  <td className="px-3 py-2">{p.semester}</td>
                  <td className="px-3 py-2 font-medium text-slate-800 max-w-xs">{p.project_title}</td>
                  <td className="px-3 py-2">{p.project_type}</td>
                  <td className="px-3 py-2">{p.faculty_name}</td>
                  <td className="px-3 py-2">{p.co_guide || "—"}</td>
                  <td className="px-3 py-2">{p.students.join(", ") || "—"}</td>
                  <td className="px-3 py-2">
                    <span title={p.sdg_review_status}>{formatSdgs(p)}</span>
                    {p.suggested_sdgs.length > 0 && p.sdg_review_status === "pending_review" && (
                      <span className="block text-xs text-amber-700">Pending review</span>
                    )}
                  </td>
                  <td className="px-3 py-2">{p.status}</td>
                  <td className="px-3 py-2">{p.credit ?? "—"}</td>
                  {canReviewSdgs && (
                    <td className="px-3 py-2 whitespace-nowrap">
                      <div className="flex flex-wrap items-center gap-2">
                        {isAdmin && (
                          <button
                            type="button"
                            className="text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 px-2 py-1 rounded"
                            onClick={() => openEdit(p)}
                          >
                            Edit
                          </button>
                        )}
                        <button
                          type="button"
                          className="text-xs font-medium text-teal-800 bg-teal-50 hover:bg-teal-100 px-2 py-1 rounded"
                          onClick={() => openSdgReview(p)}
                        >
                          {llmEnabled ? "Review SDGs" : "Edit SDGs"}
                        </button>
                        {isAdmin && (
                          <button
                            type="button"
                            className="text-xs font-medium text-red-700 bg-red-50 hover:bg-red-100 px-2 py-1 rounded"
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
                  <td colSpan={canReviewSdgs ? 11 : 10} className="px-3 py-8 text-center text-slate-500">
                    No projects match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-t text-xs text-slate-500">
          <span>
            Showing {projects.length} of {total} projects (page {filters.page})
          </span>
          {total > 200 && (
            <div className="flex gap-2">
              <button
                type="button"
                disabled={filters.page <= 1}
                className="px-2 py-1 border rounded disabled:opacity-40"
                onClick={() => setFilters({ ...filters, page: filters.page - 1 })}
              >
                Previous
              </button>
              <button
                type="button"
                disabled={filters.page * 200 >= total}
                className="px-2 py-1 border rounded disabled:opacity-40"
                onClick={() => setFilters({ ...filters, page: filters.page + 1 })}
              >
                Next
              </button>
            </div>
          )}
        </div>
      </div>

      {showForm && isAdmin && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-3 max-h-[90vh] overflow-y-auto">
            <h3 className="font-semibold">{editing ? "Edit project" : "Add project"}</h3>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Project topic"
              value={form.project_title}
              onChange={(e) => setForm({ ...form, project_title: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-2">
              <select
                className="border rounded-lg px-3 py-2 text-sm"
                value={form.project_type}
                onChange={(e) => setForm({ ...form, project_type: e.target.value })}
              >
                <option value="BTP">BTP</option>
                <option value="IP">IP</option>
              </select>
              <input
                className="border rounded-lg px-3 py-2 text-sm"
                placeholder="Semester"
                value={form.semester}
                onChange={(e) => setForm({ ...form, semester: e.target.value })}
              />
            </div>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={form.faculty_id}
              onChange={(e) => setForm({ ...form, faculty_id: e.target.value })}
            >
              <option value="">Select faculty supervisor</option>
              {faculty.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Co guide (optional)"
              value={form.co_guide}
              onChange={(e) => setForm({ ...form, co_guide: e.target.value })}
            />
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Students (semicolon-separated)"
              value={form.students}
              onChange={(e) => setForm({ ...form, students: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                className="border rounded-lg px-3 py-2 text-sm"
                placeholder="Status"
                value={form.status}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              />
              <input
                className="border rounded-lg px-3 py-2 text-sm"
                placeholder="Credit"
                value={form.credit}
                onChange={(e) => setForm({ ...form, credit: e.target.value })}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg"
                onClick={saveForm}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}

      {reviewProject && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3">
            <h3 className="font-semibold">{llmEnabled ? "SDG review" : "Edit SDGs"}</h3>
            <p className="text-sm text-slate-600">{reviewProject.project_title}</p>
            {!llmEnabled && (
              <p className="text-xs text-slate-500">
                AI SDG tagging is off. Select SDGs below and save (you can clear all to remove SDGs).
              </p>
            )}
            {llmEnabled && reviewProject.suggested_sdgs.length > 0 && (
              <ul className="text-sm space-y-1">
                {reviewProject.suggested_sdgs.map((s) => (
                  <li key={s.id}>
                    SDG {s.sdg_number} — {s.sdg_name}
                    {s.confidence_score != null && (
                      <span className="text-slate-500"> ({Math.round(s.confidence_score * 100)}%)</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <div className="text-xs text-slate-500">SDG selection:</div>
            <div className="max-h-32 overflow-y-auto border rounded-lg p-2 space-y-1">
              {sdgCatalog.map((s) => (
                <label key={s.id} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={editSdgsSelection.includes(s.sdg_number)}
                    onChange={(e) => {
                      if (e.target.checked) setEditSdgsSelection([...editSdgsSelection, s.sdg_number]);
                      else setEditSdgsSelection(editSdgsSelection.filter((n) => n !== s.sdg_number));
                    }}
                  />
                  SDG {s.sdg_number} — {s.sdg_name}
                </label>
              ))}
            </div>
            <div className="flex flex-wrap gap-2">
              {llmEnabled && reviewProject.suggested_sdgs.length > 0 && (
                <>
                  <button
                    type="button"
                    className="text-sm bg-teal-700 text-white px-3 py-1.5 rounded-lg"
                    onClick={async () => {
                      await acceptSdgs(reviewProject.id);
                      setReviewProject(null);
                      await load();
                    }}
                  >
                    Accept
                  </button>
                  <button
                    type="button"
                    className="text-sm border px-3 py-1.5 rounded-lg"
                    onClick={async () => {
                      await rejectSdgs(reviewProject.id);
                      setReviewProject(null);
                      await load();
                    }}
                  >
                    Reject
                  </button>
                </>
              )}
              <button
                type="button"
                className="text-sm bg-teal-700 text-white px-3 py-1.5 rounded-lg"
                onClick={async () => {
                  try {
                    await editSdgs(reviewProject.id, editSdgsSelection);
                    setReviewProject(null);
                    await load();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Could not save SDGs");
                  }
                }}
              >
                Save SDGs
              </button>
              {llmEnabled && (
                <button
                  type="button"
                  className="text-sm text-teal-700"
                  onClick={async () => {
                    try {
                      const updated = await generateSdgs(reviewProject.id);
                      setReviewProject(updated);
                      setEditSdgsSelection(
                        updated.confirmed_sdgs.length > 0
                          ? updated.confirmed_sdgs.map((s) => s.sdg_number)
                          : updated.suggested_sdgs.map((s) => s.sdg_number)
                      );
                      await load();
                    } catch (e) {
                      setError(e instanceof Error ? e.message : "Regenerate failed");
                    }
                  }}
                >
                  Regenerate
                </button>
              )}
              <button type="button" className="text-sm ml-auto" onClick={() => setReviewProject(null)}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
