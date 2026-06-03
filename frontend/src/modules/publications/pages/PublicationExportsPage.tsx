import { useEffect, useState } from "react";
import { listFaculty } from "../services/publicationsApi";
import type { Faculty } from "../types/publications";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

async function downloadExport(params: URLSearchParams) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE}/publications/exports?${params}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Export failed");
  }
  const blob = await res.blob();
  const format = params.get("format") ?? "csv";
  const disposition = res.headers.get("content-disposition") ?? "";
  const nameMatch = disposition.match(/filename=([^;]+)/i);
  const responseName = nameMatch?.[1]?.replaceAll('"', "").trim();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = responseName || `publications.${format}`;
  a.click();
  URL.revokeObjectURL(url);
}

export default function PublicationExportsPage() {
  const [faculty, setFaculty] = useState<Faculty[]>([]);
  const [selectedFacultyIds, setSelectedFacultyIds] = useState<string[]>([]);
  const [year, setYear] = useState("");
  const [yearStart, setYearStart] = useState("");
  const [yearEnd, setYearEnd] = useState("");
  const [scope, setScope] = useState<"all" | "faculty" | "year">("all");
  const [exportType, setExportType] = useState<"publications" | "patents" | "both">("both");
  const [error, setError] = useState("");

  useEffect(() => {
    listFaculty({ page: 1, page_size: 200 })
      .then((r) => setFaculty(r.items))
      .catch(() => {});
  }, []);

  function buildParams(format: "csv" | "xlsx" | "pdf") {
    const p = new URLSearchParams({ format, scope, export_type: exportType });
    if (selectedFacultyIds.length) p.set("faculty_ids", selectedFacultyIds.join(","));
    if (year) p.set("publication_year", year);
    if (yearStart) p.set("year_start", yearStart);
    if (yearEnd) p.set("year_end", yearEnd);
    return p;
  }

  async function runExport(format: "csv" | "xlsx" | "pdf") {
    setError("");
    try {
      await downloadExport(buildParams(format));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Publication Exports</h2>
      <p className="text-sm text-slate-600">
        Export publications as Excel, CSV, or PDF. Faculty-wise and year-wise grouping is supported.
      </p>

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <h3 className="text-sm font-semibold text-slate-700">Export options</h3>
        <div className="grid sm:grid-cols-3 gap-3">
          <label className="text-sm">
            <span className="block text-slate-600 mb-1">Export type</span>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={exportType}
              onChange={(e) => setExportType(e.target.value as "publications" | "patents" | "both")}
            >
              <option value="publications">Publications</option>
              <option value="patents">Patents</option>
              <option value="both">Both</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-slate-600 mb-1">Scope</span>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={scope}
              onChange={(e) => setScope(e.target.value as "all" | "faculty" | "year")}
            >
              <option value="all">All publications</option>
              <option value="faculty">Faculty-wise (Excel sheets / CSV-PDF zip)</option>
              <option value="year">Year-wise (Excel sheets / CSV-PDF zip)</option>
            </select>
          </label>
          <label className="text-sm">
            <span className="block text-slate-600 mb-1">Filter by faculty</span>
            <select
              multiple
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={selectedFacultyIds}
              onChange={(e) => {
                const values = Array.from(e.target.selectedOptions).map((o) => o.value);
                setSelectedFacultyIds(values);
              }}
            >
              {faculty.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
            <span className="mt-1 block text-xs text-slate-500">Ctrl/Cmd + click to choose multiple faculty</span>
          </label>
          <label className="text-sm">
            <span className="block text-slate-600 mb-1">Filter by single year</span>
            <input
              type="number"
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. 2024"
              value={year}
              onChange={(e) => setYear(e.target.value)}
            />
          </label>
          <label className="text-sm">
            <span className="block text-slate-600 mb-1">Year range start</span>
            <input
              type="number"
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. 2020"
              value={yearStart}
              onChange={(e) => setYearStart(e.target.value)}
            />
          </label>
          <label className="text-sm">
            <span className="block text-slate-600 mb-1">Year range end</span>
            <input
              type="number"
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. 2024"
              value={yearEnd}
              onChange={(e) => setYearEnd(e.target.value)}
            />
          </label>
        </div>
      </section>

      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <div className="flex flex-wrap gap-3">
        {(["csv", "xlsx", "pdf"] as const).map((fmt) => (
          <button
            key={fmt}
            type="button"
            onClick={() => runExport(fmt)}
            className={`rounded-lg px-4 py-2 text-sm ${
              fmt === "csv" ? "bg-teal-700 text-white" : "border border-slate-300"
            }`}
          >
            Export {fmt.toUpperCase()}
          </button>
        ))}
      </div>
    </div>
  );
}
