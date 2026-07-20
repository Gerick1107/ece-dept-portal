import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import {
  createLab,
  deleteLab,
  getFacultyOptions,
  listLabs,
  updateLab,
  type Lab,
  type LabFormBody,
} from "../labsApi";

const emptyForm: LabFormBody = {
  lab_name: "",
  location: "",
  faculty_id: 0,
  total_seats: 0,
  allotted_seats: 0,
  remarks: "",
};

function occupancyColor(pct: number): string {
  if (pct >= 90) return "bg-red-500";
  if (pct >= 70) return "bg-amber-500";
  return "bg-teal-600";
}

export default function LabSeatingCapacityPage() {
  const { user } = useAuth();
  const canManage = user?.role === "admin" || user?.role === "hod";
  const isAdmin = user?.role === "admin";

  const [labs, setLabs] = useState<Lab[]>([]);
  const [summary, setSummary] = useState({
    total_labs: 0,
    total_seats: 0,
    allotted_seats: 0,
    remaining_seats: 0,
    occupancy_pct: 0,
  });
  const [facultyOptions, setFacultyOptions] = useState<{ id: number; name: string }[]>([]);
  const [facultyFilter, setFacultyFilter] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Lab | null>(null);
  const [form, setForm] = useState<LabFormBody>(emptyForm);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await listLabs({
        faculty_id: facultyFilter ? Number(facultyFilter) : undefined,
        query: query || undefined,
      });
      setLabs(r.items);
      setSummary(r.summary);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load labs");
    }
  }, [facultyFilter, query]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    getFacultyOptions()
      .then((r) => setFacultyOptions(r.faculty))
      .catch(() => {});
  }, []);

  function openAdd() {
    setEditing(null);
    setForm(emptyForm);
    setShowForm(true);
  }

  function openEdit(lab: Lab) {
    setEditing(lab);
    setForm({
      lab_name: lab.lab_name,
      location: lab.location ?? "",
      faculty_id: lab.faculty_id,
      total_seats: lab.total_seats,
      allotted_seats: lab.allotted_seats,
      remarks: lab.remarks ?? "",
    });
    setShowForm(true);
  }

  async function onSave() {
    if (!form.lab_name.trim() || !form.faculty_id) {
      setError("Lab name and faculty are required.");
      return;
    }
    if (form.allotted_seats > form.total_seats) {
      setError("Allotted seats cannot exceed total seats.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      if (editing) {
        await updateLab(editing.id, form);
        setMessage("Lab updated.");
      } else {
        await createLab(form);
        setMessage("Lab added.");
      }
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Lab Seating Capacity</h2>
          <p className="text-sm text-slate-600 mt-1">
            Track total and allotted seats across ECE department labs, grouped by the faculty in charge.
          </p>
        </div>
        {canManage && (
          <button type="button" onClick={openAdd} className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm">
            Add lab
          </button>
        )}
      </div>

      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-2xl font-semibold text-teal-800">{summary.total_labs}</p>
          <p className="text-sm text-slate-600 mt-1">Total labs</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-2xl font-semibold text-teal-800">{summary.total_seats}</p>
          <p className="text-sm text-slate-600 mt-1">Total seats</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-2xl font-semibold text-teal-800">{summary.allotted_seats}</p>
          <p className="text-sm text-slate-600 mt-1">Allotted seats</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-2xl font-semibold text-teal-800">{summary.remaining_seats}</p>
          <p className="text-sm text-slate-600 mt-1">Remaining seats</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-2xl font-semibold text-teal-800">{summary.occupancy_pct}%</p>
          <p className="text-sm text-slate-600 mt-1">Occupancy</p>
        </div>
      </div>

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
        <input
          placeholder="Search lab name…"
          className="border rounded-lg px-3 py-2 text-sm"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={facultyFilter}
          onChange={(e) => setFacultyFilter(e.target.value)}
        >
          <option value="">All faculty</option>
          {facultyOptions.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </select>
      </section>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-left">
              <th className="px-4 py-2">Lab</th>
              <th className="px-4 py-2">Location</th>
              <th className="px-4 py-2">Faculty in-charge</th>
              <th className="px-4 py-2">Total seats</th>
              <th className="px-4 py-2">Allotted</th>
              <th className="px-4 py-2">Remaining</th>
              <th className="px-4 py-2 min-w-[10rem]">Occupancy</th>
              {canManage && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {labs.map((lab) => (
              <tr key={lab.id} className="border-t border-slate-100">
                <td className="px-4 py-2 font-medium text-slate-800">{lab.lab_name}</td>
                <td className="px-4 py-2">{lab.location || "—"}</td>
                <td className="px-4 py-2">{lab.faculty_name || "—"}</td>
                <td className="px-4 py-2">{lab.total_seats}</td>
                <td className="px-4 py-2">{lab.allotted_seats}</td>
                <td className="px-4 py-2">{lab.remaining_seats}</td>
                <td className="px-4 py-2">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-2 rounded-full bg-slate-100 overflow-hidden">
                      <div
                        className={`h-full ${occupancyColor(lab.occupancy_pct)}`}
                        style={{ width: `${Math.min(lab.occupancy_pct, 100)}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-500 w-10 text-right">{lab.occupancy_pct}%</span>
                  </div>
                </td>
                {canManage && (
                  <td className="px-4 py-2 whitespace-nowrap">
                    <button type="button" className="text-xs text-teal-700 mr-3" onClick={() => openEdit(lab)}>
                      Edit
                    </button>
                    {isAdmin && (
                      <button
                        type="button"
                        className="text-xs text-red-700"
                        onClick={async () => {
                          if (!window.confirm(`Delete lab "${lab.lab_name}"?`)) return;
                          await deleteLab(lab.id);
                          setMessage("Lab deleted.");
                          await load();
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {!labs.length && (
              <tr>
                <td colSpan={canManage ? 8 : 7} className="px-4 py-8 text-center text-slate-500">
                  No labs added yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && canManage && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3">
            <h3 className="font-semibold">{editing ? "Edit lab" : "Add lab"}</h3>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Lab name (e.g. VLSI Design Lab)"
              value={form.lab_name}
              onChange={(e) => setForm({ ...form, lab_name: e.target.value })}
            />
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Location (e.g. Block C, Room 204)"
              value={form.location ?? ""}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
            />
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={form.faculty_id || ""}
              onChange={(e) => setForm({ ...form, faculty_id: Number(e.target.value) })}
            >
              <option value="">Select faculty in-charge</option>
              {facultyOptions.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
            <div className="grid grid-cols-2 gap-2">
              <label className="text-xs text-slate-500 block">
                Total seats
                <input
                  type="number"
                  min={0}
                  className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.total_seats}
                  onChange={(e) => setForm({ ...form, total_seats: Number(e.target.value) || 0 })}
                />
              </label>
              <label className="text-xs text-slate-500 block">
                Allotted seats
                <input
                  type="number"
                  min={0}
                  className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                  value={form.allotted_seats}
                  onChange={(e) => setForm({ ...form, allotted_seats: Number(e.target.value) || 0 })}
                />
              </label>
            </div>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm min-h-[70px]"
              placeholder="Remarks (optional)"
              value={form.remarks ?? ""}
              onChange={(e) => setForm({ ...form, remarks: e.target.value })}
            />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50"
                onClick={onSave}
              >
                {busy ? "Saving…" : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}