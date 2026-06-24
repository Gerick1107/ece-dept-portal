import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { listFaculty } from "../../publications/services/publicationsApi";
import type { Faculty } from "../../publications/types/publications";
import {
  createContribution,
  deleteContribution,
  downloadContributionsExport,
  listContributions,
  resolveContributionFaculty,
  updateContribution,
} from "../../shared/portalApi";
import { CONTRIBUTION_TABS, type ContributionResource, type TabConfig } from "../contributionConfig";

function FacultyContributionTable({ config }: { config: TabConfig }) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [items, setItems] = useState<Record<string, unknown>[]>([]);
  const [years, setYears] = useState<string[]>([]);
  const [exactYears, setExactYears] = useState<number[]>([]);
  const [facultyOptions, setFacultyOptions] = useState<{ id: number; name: string }[]>([]);
  const [extraValues, setExtraValues] = useState<string[]>([]);
  const [unmatchedCount, setUnmatchedCount] = useState(0);
  const [eceFaculty, setEceFaculty] = useState<Faculty[]>([]);
  const [query, setQuery] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [exactYearFilter, setExactYearFilter] = useState("");
  const [extraFilter, setExtraFilter] = useState("");
  const [selectedFacultyId, setSelectedFacultyId] = useState("");
  const [showUnmatched, setShowUnmatched] = useState(false);
  const [exportExactYearFrom, setExportExactYearFrom] = useState("");
  const [exportExactYearTo, setExportExactYearTo] = useState("");
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<Record<string, unknown> | null>(null);
  const [form, setForm] = useState<Record<string, string>>({ faculty_id: "" });
  const [resolveRowId, setResolveRowId] = useState<number | null>(null);
  const [resolveFacultyId, setResolveFacultyId] = useState("");

  const facultyNameById = useMemo(() => {
    const m = new Map<number, string>();
    for (const f of eceFaculty) m.set(f.id, f.name);
    for (const f of facultyOptions) m.set(f.id, f.name);
    return m;
  }, [eceFaculty, facultyOptions]);

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await listContributions(config.resource, {
        query: query || undefined,
        year: yearFilter || undefined,
        exact_year: exactYearFilter ? Number(exactYearFilter) : undefined,
        faculty_id: selectedFacultyId ? Number(selectedFacultyId) : undefined,
        extra_filter: extraFilter || undefined,
        unmatched_only: showUnmatched || undefined,
      });
      setItems(r.items);
      setYears(r.years);
      setExactYears(r.exact_years ?? []);
      setFacultyOptions(r.faculty);
      setExtraValues(r.extra_filter_values);
      setUnmatchedCount(r.unmatched_count);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load records");
    }
  }, [config.resource, query, yearFilter, exactYearFilter, selectedFacultyId, extraFilter, showUnmatched]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    listFaculty({ page: 1, page_size: 200, include_inactive: false })
      .then((r) => setEceFaculty(r.items.filter((f: Faculty) => f.department?.includes("ECE"))))
      .catch(() => {});
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, Record<string, unknown>[]>();
    for (const row of items) {
      const fid = row.faculty_id as number | null;
      const heading = fid ? facultyNameById.get(fid) ?? String(row.faculty_name) : `⚠ ${row.faculty_name} (unmatched)`;
      const list = map.get(heading) ?? [];
      list.push(row);
      map.set(heading, list);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [items, facultyNameById]);

  function openAdd() {
    setEditing(null);
    const init: Record<string, string> = { faculty_id: "" };
    for (const f of config.formFields) init[f.key] = "";
    setForm(init);
    setShowModal(true);
  }

  function openEdit(row: Record<string, unknown>) {
    setEditing(row);
    const init: Record<string, string> = {
      faculty_id: row.faculty_id != null ? String(row.faculty_id) : "",
    };
    for (const f of config.formFields) {
      const v = row[f.key];
      init[f.key] = v != null ? String(v) : "";
    }
    setForm(init);
    setShowModal(true);
  }

  async function saveRow() {
    const body: Record<string, unknown> = { faculty_id: Number(form.faculty_id) };
    for (const f of config.formFields) {
      const raw = form[f.key]?.trim() ?? "";
      if (f.type === "number") {
        body[f.key] = raw ? Number(raw) : null;
      } else {
        body[f.key] = raw || null;
      }
    }
    try {
      if (editing) {
        await updateContribution(config.resource, Number(editing.id), body);
        setMessage("Record updated.");
      } else {
        await createContribution(config.resource, body);
        setMessage("Record added.");
      }
      setShowModal(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  const extraFilterOptions = config.showExtraFilter?.values ?? extraValues;

  return (
    <div className="space-y-4">
      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      {isAdmin && unmatchedCount > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm">
          <strong>{unmatchedCount}</strong> record(s) need faculty review.{" "}
          <button type="button" className="underline text-amber-900" onClick={() => setShowUnmatched(!showUnmatched)}>
            {showUnmatched ? "Show all" : "Show unmatched only"}
          </button>
        </div>
      )}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <input
          placeholder={config.searchPlaceholder}
          className="border rounded-lg px-3 py-2 text-sm lg:col-span-2"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {config.showYearFilters && (
          <select className="border rounded-lg px-3 py-2 text-sm" value={yearFilter} onChange={(e) => setYearFilter(e.target.value)}>
            <option value="">All academic years</option>
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        )}
        {config.showExactYearFilter && (
          <select className="border rounded-lg px-3 py-2 text-sm" value={exactYearFilter} onChange={(e) => setExactYearFilter(e.target.value)}>
            <option value="">All years</option>
            {exactYears.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        )}
        {config.showExtraFilter && (
          <select className="border rounded-lg px-3 py-2 text-sm" value={extraFilter} onChange={(e) => setExtraFilter(e.target.value)}>
            <option value="">{config.showExtraFilter.allLabel}</option>
            {extraFilterOptions.map((v) => (
              <option key={v} value={v}>{v}</option>
            ))}
          </select>
        )}
        <select className="border rounded-lg px-3 py-2 text-sm sm:col-span-2" value={selectedFacultyId} onChange={(e) => setSelectedFacultyId(e.target.value)}>
          <option value="">All faculty</option>
          {facultyOptions.map((f) => (
            <option key={f.id} value={f.id}>{f.name}</option>
          ))}
        </select>
        {config.noDateNote && (
          <p className="text-xs text-slate-500 sm:col-span-full italic">{config.noDateNote}</p>
        )}
      </section>

      <div className="flex flex-wrap gap-2 justify-end">
        <button
          type="button"
          onClick={() => {
            setExportExactYearFrom(exactYearFilter);
            setExportExactYearTo(exactYearFilter);
            setShowExportModal(true);
          }}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
        >
          Export Excel
        </button>
        {isAdmin && (
          <button type="button" onClick={openAdd} className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm">
            {config.addLabel}
          </button>
        )}
      </div>

      <div className="space-y-4">
        {grouped.map(([facultyName, rows]) => (
          <details key={facultyName} open className="bg-white border border-slate-200 rounded-xl shadow-sm">
            <summary className="cursor-pointer px-4 py-3 font-medium text-slate-800 border-b border-slate-100">
              ▼ {facultyName} <span className="text-sm font-normal text-slate-500">({rows.length} {config.recordLabel})</span>
            </summary>
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[700px]">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 text-left">
                    {config.columns.map((col) => (
                      <th key={col.key} className="px-4 py-2 font-medium">{col.label}</th>
                    ))}
                    {isAdmin && <th className="px-4 py-2 font-medium w-40">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={String(row.id)} className="border-t border-slate-100">
                      {config.columns.map((col) => (
                        <td key={col.key} className="px-4 py-2 align-top">
                          {col.render ? col.render(row) : String(row[col.key] ?? "—")}
                        </td>
                      ))}
                      {isAdmin && (
                        <td className="px-4 py-2 whitespace-nowrap">
                          {!row.faculty_id && (
                            <button
                              type="button"
                              className="text-xs px-2 py-1 rounded bg-amber-50 text-amber-800 mr-2"
                              onClick={() => {
                                setResolveRowId(Number(row.id));
                                setResolveFacultyId("");
                              }}
                            >
                              Match
                            </button>
                          )}
                          <button type="button" className="text-xs px-2 py-1 rounded bg-slate-100 mr-2" onClick={() => openEdit(row)}>
                            Edit
                          </button>
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded bg-red-50 text-red-700"
                            onClick={async () => {
                              if (!window.confirm("Delete this record?")) return;
                              await deleteContribution(config.resource, Number(row.id));
                              setMessage("Record deleted.");
                              await load();
                            }}
                          >
                            Delete
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>
        ))}
        {!grouped.length && <p className="text-center text-slate-500 py-8">No records match your filters.</p>}
      </div>

      <p className="text-xs text-slate-400 text-center pt-4">ECE Department · Academic use only · Data synced from departmental records</p>

      {showExportModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-4">
            <h3 className="font-semibold">Export</h3>
            <div className="grid sm:grid-cols-2 gap-3">
              <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Year from" value={exportExactYearFrom} onChange={(e) => setExportExactYearFrom(e.target.value)} />
              <input type="number" className="border rounded-lg px-3 py-2 text-sm" placeholder="Year to" value={exportExactYearTo} onChange={(e) => setExportExactYearTo(e.target.value)} />
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowExportModal(false)}>Cancel</button>
              <button
                type="button"
                disabled={exportBusy}
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50"
                onClick={async () => {
                  setExportBusy(true);
                  try {
                    await downloadContributionsExport(config.resource, {
                      query: query || undefined,
                      extra_filter: extraFilter || undefined,
                      exact_year_from: exportExactYearFrom ? Number(exportExactYearFrom) : undefined,
                      exact_year_to: exportExactYearTo ? Number(exportExactYearTo) : undefined,
                      faculty_id: selectedFacultyId ? Number(selectedFacultyId) : undefined,
                    });
                    setShowExportModal(false);
                    setMessage("Export downloaded.");
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Export failed");
                  } finally {
                    setExportBusy(false);
                  }
                }}
              >
                Download
              </button>
            </div>
          </div>
        </div>
      )}

      {showModal && isAdmin && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3 max-h-[90vh] overflow-y-auto">
            <h3 className="font-semibold">{editing ? "Edit record" : config.addLabel}</h3>
            <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.faculty_id} onChange={(e) => setForm({ ...form, faculty_id: e.target.value })}>
              <option value="">Select faculty</option>
              {eceFaculty.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
            {config.formFields.map((f) =>
              f.type === "textarea" ? (
                <textarea
                  key={f.key}
                  className="w-full border rounded-lg px-3 py-2 text-sm min-h-[80px]"
                  placeholder={f.label}
                  value={form[f.key] ?? ""}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                />
              ) : (
                <input
                  key={f.key}
                  type={f.type === "number" ? "number" : "text"}
                  className="w-full border rounded-lg px-3 py-2 text-sm"
                  placeholder={f.label}
                  value={form[f.key] ?? ""}
                  onChange={(e) => setForm({ ...form, [f.key]: e.target.value })}
                />
              )
            )}
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowModal(false)}>Cancel</button>
              <button type="button" className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg" onClick={saveRow}>Save</button>
            </div>
          </div>
        </div>
      )}

      {resolveRowId != null && isAdmin && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-sm w-full p-6 space-y-3">
            <h3 className="font-semibold">Match faculty</h3>
            <select className="w-full border rounded-lg px-3 py-2 text-sm" value={resolveFacultyId} onChange={(e) => setResolveFacultyId(e.target.value)}>
              <option value="">Select faculty</option>
              {eceFaculty.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setResolveRowId(null)}>Cancel</button>
              <button
                type="button"
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg"
                onClick={async () => {
                  if (!resolveFacultyId) return;
                  await resolveContributionFaculty(config.resource, resolveRowId, Number(resolveFacultyId));
                  setResolveRowId(null);
                  setMessage("Faculty matched.");
                  await load();
                }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function FacultyContributionsPage() {
  const [activeTab, setActiveTab] = useState<ContributionResource>(CONTRIBUTION_TABS[0].resource);
  const config = CONTRIBUTION_TABS.find((t) => t.resource === activeTab)!;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Faculty Development &amp; Contributions</h2>
        <p className="text-sm text-slate-600 mt-1">Browse faculty contributions across STTP/FDP, MOOC development, memberships, and more.</p>
      </div>
      <nav className="flex flex-wrap gap-2 border-b border-slate-200 pb-2">
        {CONTRIBUTION_TABS.map((tab) => (
          <button
            key={tab.resource}
            type="button"
            onClick={() => setActiveTab(tab.resource)}
            className={`px-3 py-1.5 rounded-full text-sm ${
              activeTab === tab.resource ? "bg-teal-700 text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
      <FacultyContributionTable key={config.resource} config={config} />
    </div>
  );
}
