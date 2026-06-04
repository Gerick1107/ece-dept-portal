import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { listFaculty } from "../../publications/services/publicationsApi";
import type { Faculty } from "../../publications/types/publications";
import { createAward, deleteAward, downloadAwardsExport, listAwards, updateAward } from "../../shared/portalApi";
import type { FacultyAward } from "../../projects/types/projects";

export default function AwardsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [awards, setAwards] = useState<FacultyAward[]>([]);
  const [years, setYears] = useState<string[]>([]);
  const [facultyNames, setFacultyNames] = useState<string[]>([]);
  const [eceFaculty, setEceFaculty] = useState<Faculty[]>([]);
  const [query, setQuery] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [selectedFaculty, setSelectedFaculty] = useState("");
  const [exportYearFrom, setExportYearFrom] = useState("");
  const [exportYearTo, setExportYearTo] = useState("");
  const [exportFaculty, setExportFaculty] = useState<string[]>([]);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<FacultyAward | null>(null);
  const [form, setForm] = useState({ faculty_name: "", year: "", award: "" });

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await listAwards(query || undefined, yearFilter || undefined);
      setAwards(r.items);
      setYears(r.years);
      setFacultyNames(r.faculty_names);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load awards");
    }
  }, [query, yearFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    listFaculty({ page: 1, page_size: 200, include_inactive: false })
      .then((r) => setEceFaculty(r.items.filter((f: Faculty) => f.department?.includes("ECE"))))
      .catch(() => {});
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, FacultyAward[]>();
    for (const a of awards) {
      if (selectedFaculty && a.faculty_name !== selectedFaculty) continue;
      const list = map.get(a.faculty_name) ?? [];
      list.push(a);
      map.set(a.faculty_name, list);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [awards, selectedFaculty]);

  function openAdd() {
    setEditing(null);
    setForm({ faculty_name: "", year: "", award: "" });
    setShowModal(true);
  }

  function openEdit(row: FacultyAward) {
    setEditing(row);
    setForm({ faculty_name: row.faculty_name, year: row.year, award: row.award });
    setShowModal(true);
  }

  async function saveAward() {
    try {
      if (editing) {
        await updateAward(editing.id, form);
        setMessage("Award updated.");
      } else {
        await createAward(form);
        setMessage("Award added.");
      }
      setShowModal(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Faculty Awards & Recognitions</h2>
          <p className="text-sm text-slate-600 mt-1">Browse and manage department faculty awards.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              setExportYearFrom(yearFilter);
              setExportYearTo(yearFilter);
              setExportFaculty(selectedFaculty ? [selectedFaculty] : []);
              setShowExportModal(true);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
          >
            Export Excel
          </button>
          {isAdmin && (
            <button type="button" onClick={openAdd} className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm">
              Add Award
            </button>
          )}
        </div>
      </div>

      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm grid sm:grid-cols-3 gap-3">
        <input
          placeholder="Search faculty or award…"
          className="border rounded-lg px-3 py-2 text-sm"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="border rounded-lg px-3 py-2 text-sm" value={yearFilter} onChange={(e) => setYearFilter(e.target.value)}>
          <option value="">All years</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={selectedFaculty} onChange={(e) => setSelectedFaculty(e.target.value)}>
          <option value="">All faculty with awards</option>
          {facultyNames.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </section>

      <div className="space-y-4">
        {grouped.map(([facultyName, rows]) => (
          <details key={facultyName} open className="bg-white border border-slate-200 rounded-xl shadow-sm">
            <summary className="cursor-pointer px-4 py-3 font-medium text-slate-800 border-b border-slate-100">
              {facultyName} <span className="text-sm font-normal text-slate-500">({rows.length} awards)</span>
            </summary>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 text-left">
                    <th className="px-4 py-2 font-medium w-32">Year</th>
                    <th className="px-4 py-2 font-medium">Award / Recognition</th>
                    {isAdmin && <th className="px-4 py-2 font-medium w-32">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id} className="border-t border-slate-100">
                      <td className="px-4 py-2 align-top">{row.year}</td>
                      <td className="px-4 py-2">{row.award}</td>
                      {isAdmin && (
                        <td className="px-4 py-2 whitespace-nowrap">
                          <button type="button" className="text-xs px-2 py-1 rounded bg-slate-100 mr-2" onClick={() => openEdit(row)}>
                            Edit
                          </button>
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded bg-red-50 text-red-700"
                            onClick={async () => {
                              if (!window.confirm("Are you sure you want to delete this award?")) return;
                              await deleteAward(row.id);
                              setMessage("Award deleted.");
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
        {!grouped.length && <p className="text-center text-slate-500 py-8">No awards match your filters.</p>}
      </div>

      {showExportModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-4">
            <h3 className="font-semibold">Export awards</h3>
            <p className="text-sm text-slate-600">
              Exports rows matching your filters. Leave fields empty to include all matching the search box above.
            </p>
            <div className="grid sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs text-slate-500">Year from</label>
                <input
                  className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
                  placeholder="e.g. 2020-2021"
                  value={exportYearFrom}
                  onChange={(e) => setExportYearFrom(e.target.value)}
                />
              </div>
              <div>
                <label className="text-xs text-slate-500">Year to</label>
                <input
                  className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
                  placeholder="e.g. 2024-2025"
                  value={exportYearTo}
                  onChange={(e) => setExportYearTo(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="text-xs text-slate-500">Faculty (hold Ctrl/Cmd for multiple)</label>
              <select
                multiple
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1 min-h-[120px]"
                value={exportFaculty}
                onChange={(e) =>
                  setExportFaculty(Array.from(e.target.selectedOptions).map((o) => o.value))
                }
              >
                {facultyNames.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-500 mt-1">Leave none selected to export all faculty in the filtered set.</p>
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowExportModal(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={exportBusy}
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50"
                onClick={async () => {
                  setExportBusy(true);
                  setError("");
                  try {
                    await downloadAwardsExport({
                      query: query || undefined,
                      year: exportYearFrom && exportYearFrom === exportYearTo ? exportYearFrom : undefined,
                      year_from: exportYearFrom || undefined,
                      year_to: exportYearTo || undefined,
                      faculty_names: exportFaculty.length ? exportFaculty : undefined,
                    });
                    setShowExportModal(false);
                    setMessage("Awards exported.");
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
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3">
            <h3 className="font-semibold">{editing ? "Edit award" : "Add award"}</h3>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={form.faculty_name}
              onChange={(e) => setForm({ ...form, faculty_name: e.target.value })}
            >
              <option value="">Select faculty</option>
              {eceFaculty.map((f) => (
                <option key={f.id} value={f.name}>
                  {f.name}
                </option>
              ))}
            </select>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="2024-2025"
              value={form.year}
              onChange={(e) => setForm({ ...form, year: e.target.value })}
            />
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm min-h-[100px]"
              placeholder="Award / Recognition"
              value={form.award}
              onChange={(e) => setForm({ ...form, award: e.target.value })}
            />
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowModal(false)}>
                Cancel
              </button>
              <button type="button" className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg" onClick={saveAward}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
