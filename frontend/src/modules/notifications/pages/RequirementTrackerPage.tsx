import { useEffect, useState } from "react";
import { apiGet, apiPutJson } from "../../../services/api";

type MatrixRow = {
  user_id: number;
  name: string;
  email: string;
  cells: Record<string, { status: string }>;
};

const STATUS_COLORS: Record<string, string> = {
  grey: "bg-slate-200",
  red: "bg-red-500",
  yellow: "bg-yellow-400",
  green: "bg-green-500",
};

const REQUIREMENT_SHORT: Record<string, string> = {
  course_upcoming_sem: "Courses",
  yearly_report: "Report",
  new_awards: "Awards",
  new_fdps: "FDPs",
  verify_sdgs: "SDGs",
  copo_attainment: "CO-PO",
};

export default function RequirementTrackerPage() {
  const [rows, setRows] = useState<MatrixRow[]>([]);
  const [labels, setLabels] = useState<Record<string, string>>({});
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");

  async function load() {
    try {
      const data = await apiGet<{ rows: MatrixRow[]; labels: Record<string, string> }>("/notifications/admin/requirements");
      setRows(data.rows);
      setLabels(data.labels);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tracker");
    }
  }

  useEffect(() => {
    load();
  }, []);

  const types = Object.keys(labels);
  const filtered = rows.filter(
    (r) =>
      !query ||
      r.name.toLowerCase().includes(query.toLowerCase()) ||
      r.email.toLowerCase().includes(query.toLowerCase())
  );

  async function setStatus(userId: number, reqType: string, status: string) {
    await apiPutJson(`/notifications/admin/requirements/${userId}/${reqType}`, { status });
    await load();
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Requirement Tracker</h2>
        <p className="text-sm text-slate-600 mt-1">Track faculty responses to data requests. Grey = not asked · Red = asked · Yellow = read · Green = fulfilled (manual).</p>
      </div>
      <div className="flex flex-wrap gap-3 text-xs">
        {Object.entries(STATUS_COLORS).map(([k, c]) => (
          <span key={k} className="flex items-center gap-1">
            <span className={`w-3 h-3 rounded ${c}`} /> {k}
          </span>
        ))}
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
      <input
        className="border rounded-lg px-3 py-2 text-sm w-full max-w-md"
        placeholder="Search faculty…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <div className="overflow-x-auto bg-white border rounded-xl">
        <table className="text-sm min-w-[800px] w-full">
          <thead>
            <tr className="bg-slate-50 text-left">
              <th className="px-3 py-2">Faculty</th>
              {types.map((t) => (
                <th key={t} className="px-2 py-2 text-center" title={labels[t]}>
                  {REQUIREMENT_SHORT[t] ?? t}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.map((row) => (
              <tr key={row.user_id} className="border-t">
                <td className="px-3 py-2">
                  <div className="font-medium">{row.name}</div>
                  <div className="text-xs text-slate-500">{row.email}</div>
                </td>
                {types.map((t) => {
                  const status = row.cells[t]?.status ?? "grey";
                  return (
                    <td key={t} className="px-2 py-2 text-center">
                      <button
                        type="button"
                        title={`${labels[t]} — ${status}. Click to mark green or reset grey.`}
                        className={`w-6 h-6 rounded ${STATUS_COLORS[status] ?? STATUS_COLORS.grey} mx-auto block`}
                        onClick={() => {
                          const next = status === "green" ? "grey" : "green";
                          if (window.confirm(`Set ${labels[t]} for ${row.name} to ${next}?`)) {
                            setStatus(row.user_id, t, next);
                          }
                        }}
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
