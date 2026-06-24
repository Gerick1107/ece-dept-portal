import { useCallback, useEffect, useState } from "react";
import { apiPutJson } from "../../../services/api";

type CatalogEntry = {
  id: number;
  course_code: string;
  course_name: string;
  ug_pg: string;
  core_elective: string;
  is_first_year: boolean;
};

export default function CourseCatalogPage() {
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<Partial<CatalogEntry>>({});

  const load = useCallback(async () => {
    setError("");
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE ?? "/api/v1"}/course-allocation/catalog`, {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token") ?? ""}` },
      });
      const data = await res.json();
      if (!res.ok) throw new Error("Failed to load catalog");
      setCatalog(data.items ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load catalog");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function saveCatalog(entry: CatalogEntry) {
    try {
      await apiPutJson(`/course-allocation/catalog/${entry.id}`, {
        course_code: entry.course_code,
        course_name: entry.course_name,
        ug_pg: entry.ug_pg,
        core_elective: entry.core_elective,
        is_first_year: entry.is_first_year,
      });
      setEditingId(null);
      setMessage("Catalog updated.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Course Catalog</h2>
        <p className="text-sm text-slate-600 mt-1">Canonical course metadata — edits propagate to matching allocation rows.</p>
      </div>
      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}
      <section className="bg-white border border-slate-200 rounded-xl overflow-x-auto shadow-sm">
        <table className="w-full text-sm min-w-[900px]">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-left">
              <th className="px-3 py-2">Code</th>
              <th className="px-3 py-2">Name</th>
              <th className="px-3 py-2">UG/PG</th>
              <th className="px-3 py-2">Core/Elective</th>
              <th className="px-3 py-2">FY</th>
              <th className="px-3 py-2" />
            </tr>
          </thead>
          <tbody>
            {catalog.map((c) => {
              const editing = editingId === c.id;
              const row = editing ? { ...c, ...editDraft } : c;
              return (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="px-3 py-2">{editing ? <input className="border rounded px-2 py-1 w-full" value={row.course_code} onChange={(e) => setEditDraft((d) => ({ ...d, course_code: e.target.value }))} /> : row.course_code}</td>
                  <td className="px-3 py-2">{editing ? <input className="border rounded px-2 py-1 w-full" value={row.course_name} onChange={(e) => setEditDraft((d) => ({ ...d, course_name: e.target.value }))} /> : row.course_name}</td>
                  <td className="px-3 py-2">
                    {editing ? (
                      <select className="border rounded px-2 py-1" value={row.ug_pg} onChange={(e) => setEditDraft((d) => ({ ...d, ug_pg: e.target.value }))}>
                        <option value="UG">UG</option><option value="PG">PG</option><option value="UG/PG">UG/PG</option>
                      </select>
                    ) : row.ug_pg}
                  </td>
                  <td className="px-3 py-2">
                    {editing ? (
                      <select className="border rounded px-2 py-1" value={row.core_elective} onChange={(e) => setEditDraft((d) => ({ ...d, core_elective: e.target.value }))}>
                        <option value="Core">Core</option><option value="Elective">Elective</option><option value="Core/Elective">Core/Elective</option>
                      </select>
                    ) : row.core_elective}
                  </td>
                  <td className="px-3 py-2">{editing ? <input type="checkbox" checked={row.is_first_year} onChange={(e) => setEditDraft((d) => ({ ...d, is_first_year: e.target.checked }))} /> : row.is_first_year ? "Yes" : "—"}</td>
                  <td className="px-3 py-2">
                    {editing ? (
                      <>
                        <button type="button" className="text-xs text-teal-800 mr-2" onClick={() => saveCatalog(row as CatalogEntry)}>Save</button>
                        <button type="button" className="text-xs" onClick={() => { setEditingId(null); setEditDraft({}); }}>Cancel</button>
                      </>
                    ) : (
                      <button type="button" className="text-xs text-teal-800" onClick={() => { setEditingId(c.id); setEditDraft({}); }}>Edit</button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </div>
  );
}
