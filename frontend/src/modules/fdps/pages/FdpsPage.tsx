import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { listFaculty } from "../../publications/services/publicationsApi";
import type { Faculty } from "../../publications/types/publications";
import {
  createFdp,
  deleteFdp,
  downloadFdpsExport,
  listFdps,
  updateFdp,
} from "../../shared/portalApi";
import type { FacultyFdp } from "../../projects/types/projects";

export default function FdpsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [fdps, setFdps] = useState<FacultyFdp[]>([]);
  const [years, setYears] = useState<string[]>([]);
  const [exactYears, setExactYears] = useState<number[]>([]);
  const [facultyNames, setFacultyNames] = useState<string[]>([]);
  const [eceFaculty, setEceFaculty] = useState<Faculty[]>([]);
  const [query, setQuery] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [exactYearFilter, setExactYearFilter] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("");
  const [selectedFaculty, setSelectedFaculty] = useState("");
  const [exportExactYearFrom, setExportExactYearFrom] = useState("");
  const [exportExactYearTo, setExportExactYearTo] = useState("");
  const [exportFaculty, setExportFaculty] = useState<string[]>([]);
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportBusy, setExportBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [editing, setEditing] = useState<FacultyFdp | null>(null);
  const [form, setForm] = useState({
    faculty_name: "",
    year: "",
    exact_year: "",
    program: "",
    description: "",
    no_of_days: "",
    no_of_attendees: "",
  });

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await listFdps(
        query || undefined,
        yearFilter || undefined,
        exactYearFilter ? Number(exactYearFilter) : undefined,
        categoryFilter || undefined
      );
      setFdps(r.items);
      setYears(r.years);
      setExactYears(r.exact_years ?? []);
      setFacultyNames(r.faculty_names);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load FDPs");
    }
  }, [query, yearFilter, exactYearFilter, categoryFilter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    listFaculty({ page: 1, page_size: 200, include_inactive: false })
      .then((r) => setEceFaculty(r.items.filter((f: Faculty) => f.department?.includes("ECE"))))
      .catch(() => {});
  }, []);

  const grouped = useMemo(() => {
    const map = new Map<string, FacultyFdp[]>();
    for (const row of fdps) {
      if (selectedFaculty && row.faculty_name !== selectedFaculty) continue;
      const list = map.get(row.faculty_name) ?? [];
      list.push(row);
      map.set(row.faculty_name, list);
    }
    return [...map.entries()].sort(([a], [b]) => a.localeCompare(b));
  }, [fdps, selectedFaculty]);

  function openAdd() {
    setEditing(null);
    setForm({ faculty_name: "", year: "", exact_year: "", program: "", description: "", no_of_days: "", no_of_attendees: "" });
    setShowModal(true);
  }

  function openEdit(row: FacultyFdp) {
    setEditing(row);
    setForm({
      faculty_name: row.faculty_name,
      year: row.year,
      exact_year: row.exact_year != null ? String(row.exact_year) : "",
      program: row.program,
      description: row.description,
      no_of_days: row.no_of_days != null ? String(row.no_of_days) : "",
      no_of_attendees: row.no_of_attendees != null ? String(row.no_of_attendees) : "",
    });
    setShowModal(true);
  }

  async function saveFdp() {
    const body = {
      faculty_name: form.faculty_name,
      year: form.year,
      exact_year: form.exact_year ? Number(form.exact_year) : null,
      program: form.program,
      description: form.description,
      no_of_days: form.no_of_days ? Number(form.no_of_days) : null,
      no_of_attendees: form.no_of_attendees ? Number(form.no_of_attendees) : null,
    };
    try {
      if (editing) {
        await updateFdp(editing.id, body);
        setMessage("FDP updated.");
      } else {
        await createFdp(body);
        setMessage("FDP added.");
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
          <h2 className="text-xl font-semibold">Faculty Development Programs</h2>
          <p className="text-sm text-slate-600 mt-1">Browse and manage faculty FDP participation records.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => {
              setExportExactYearFrom(exactYearFilter);
              setExportExactYearTo(exactYearFilter);
              setExportFaculty(selectedFaculty ? [selectedFaculty] : []);
              setShowExportModal(true);
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
          >
            Export Excel
          </button>
          {isAdmin && (
            <button type="button" onClick={openAdd} className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm">
              Add FDP
            </button>
          )}
        </div>
      </div>

      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <input
          placeholder="Search faculty, program, description…"
          className="border rounded-lg px-3 py-2 text-sm lg:col-span-2"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="border rounded-lg px-3 py-2 text-sm" value={yearFilter} onChange={(e) => setYearFilter(e.target.value)}>
          <option value="">All academic years</option>
          {years.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={exactYearFilter}
          onChange={(e) => setExactYearFilter(e.target.value)}
        >
          <option value="">All years</option>
          {exactYears.map((y) => (
            <option key={y} value={y}>
              {y}
            </option>
          ))}
        </select>
        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        >
          <option value="">All programs</option>
          <option value="NPTEL">NPTEL</option>
          <option value="MOOC">MOOC</option>
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm sm:col-span-2" value={selectedFaculty} onChange={(e) => setSelectedFaculty(e.target.value)}>
          <option value="">All faculty with FDPs</option>
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
              {facultyName} <span className="text-sm font-normal text-slate-500">({rows.length} FDPs)</span>
            </summary>
            <div className="overflow-x-auto">
              <table className="w-full text-sm min-w-[900px]">
                <thead>
                  <tr className="bg-slate-50 text-slate-600 text-left">
                    <th className="px-4 py-2 font-medium w-24">Year</th>
                    <th className="px-4 py-2 font-medium w-36">Program</th>
                    <th className="px-4 py-2 font-medium">Description</th>
                    <th className="px-4 py-2 font-medium w-20">Days</th>
                    <th className="px-4 py-2 font-medium w-24">Attendees</th>
                    {isAdmin && <th className="px-4 py-2 font-medium w-32">Actions</th>}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={row.id} className="border-t border-slate-100">
                      <td className="px-4 py-2 align-top">{row.exact_year ?? row.year}</td>
                      <td className="px-4 py-2 align-top">{row.program}</td>
                      <td className="px-4 py-2">{row.description}</td>
                      <td className="px-4 py-2 align-top">{row.no_of_days ?? "—"}</td>
                      <td className="px-4 py-2 align-top">{row.no_of_attendees ?? "—"}</td>
                      {isAdmin && (
                        <td className="px-4 py-2 whitespace-nowrap">
                          <button type="button" className="text-xs px-2 py-1 rounded bg-slate-100 mr-2" onClick={() => openEdit(row)}>
                            Edit
                          </button>
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded bg-red-50 text-red-700"
                            onClick={async () => {
                              if (!window.confirm("Delete this FDP record?")) return;
                              await deleteFdp(row.id);
                              setMessage("FDP deleted.");
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
        {!grouped.length && <p className="text-center text-slate-500 py-8">No FDPs match your filters.</p>}
      </div>

      {showExportModal && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-4">
            <h3 className="font-semibold">Export FDPs</h3>
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
                    await downloadFdpsExport({
                      query: query || undefined,
                      program_filter: categoryFilter || undefined,
                      exact_year_from: exportExactYearFrom ? Number(exportExactYearFrom) : undefined,
                      exact_year_to: exportExactYearTo ? Number(exportExactYearTo) : undefined,
                      faculty_names: exportFaculty.length ? exportFaculty : undefined,
                    });
                    setShowExportModal(false);
                    setMessage("FDPs exported.");
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
            <h3 className="font-semibold">{editing ? "Edit FDP" : "Add FDP"}</h3>
            <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.faculty_name} onChange={(e) => setForm({ ...form, faculty_name: e.target.value })}>
              <option value="">Select faculty</option>
              {eceFaculty.map((f) => (
                <option key={f.id} value={f.name}>{f.name}</option>
              ))}
            </select>
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Academic year (e.g. 2024-2025)" value={form.year} onChange={(e) => setForm({ ...form, year: e.target.value })} />
            <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Year (e.g. 2025)" value={form.exact_year} onChange={(e) => setForm({ ...form, exact_year: e.target.value })} />
            <input className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="Program (e.g. NPTEL, MOOC)" value={form.program} onChange={(e) => setForm({ ...form, program: e.target.value })} />
            <textarea className="w-full border rounded-lg px-3 py-2 text-sm min-h-[100px]" placeholder="Description" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
            <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="No. of days (optional)" value={form.no_of_days} onChange={(e) => setForm({ ...form, no_of_days: e.target.value })} />
            <input type="number" className="w-full border rounded-lg px-3 py-2 text-sm" placeholder="No. of attendees (optional)" value={form.no_of_attendees} onChange={(e) => setForm({ ...form, no_of_attendees: e.target.value })} />
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowModal(false)}>Cancel</button>
              <button type="button" className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg" onClick={saveFdp}>Save</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
