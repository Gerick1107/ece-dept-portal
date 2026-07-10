import { useEffect, useState } from "react";
import { listFaculty } from "../services/publicationsApi";
import type { Faculty } from "../types/publications";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

function authHeader(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function downloadBlob(blob: Blob, disposition: string, fallback: string) {
  const nameMatch = disposition.match(/filename=([^;]+)/i);
  const responseName = nameMatch?.[1]?.replaceAll('"', "").trim();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = responseName || fallback;
  a.click();
  URL.revokeObjectURL(url);
}

async function downloadExport(params: URLSearchParams) {
  const res = await fetch(`${API_BASE}/publications/exports?${params}`, { headers: authHeader() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Export failed");
  }
  const blob = await res.blob();
  const format = params.get("format") ?? "csv";
  downloadBlob(blob, res.headers.get("content-disposition") ?? "", `publications.${format}`);
}

type TemplateAnalysis = {
  format: string;
  headers: string[];
  matched: Record<string, string>;
  suggestions: Record<string, { field: string; score: number }>;
  unknown: string[];
  llm_guesses: Record<string, string>;
  available_fields: string[];
};

function CustomTemplateExport(props: {
  selectedFacultyIds: string[];
  exportType: "publications" | "patents" | "both";
  year: string;
  yearStart: string;
  yearEnd: string;
  dateStart: string;
  dateEnd: string;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [useLlm, setUseLlm] = useState(false);
  const [analysis, setAnalysis] = useState<TemplateAnalysis | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  async function analyze() {
    if (!file) return;
    setBusy(true);
    setError("");
    setNotice("");
    setAnalysis(null);
    try {
      const form = new FormData();
      form.append("template", file);
      const res = await fetch(
        `${API_BASE}/publications/exports/template/analyze?use_llm=${useLlm}`,
        { method: "POST", headers: authHeader(), body: form }
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Could not read the template");
      const a = data as TemplateAnalysis;
      setAnalysis(a);
      const initial: Record<string, string> = { ...a.matched, ...a.llm_guesses };
      for (const [h, s] of Object.entries(a.suggestions)) initial[h] = s.field;
      for (const h of a.unknown) if (!(h in initial)) initial[h] = "";
      setMapping(initial);
      const needsReview = Object.keys(a.suggestions).length + a.unknown.length + Object.keys(a.llm_guesses).length;
      setNotice(
        needsReview > 0
          ? "Some columns need your confirmation before compiling. Review the highlighted rows below."
          : "All columns matched. You can compile now."
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  async function compile() {
    if (!file || !analysis) return;
    const missing = analysis.headers.filter((h) => !mapping[h]);
    if (missing.length) {
      setError(`Please choose a data field for: ${missing.join(", ")}`);
      return;
    }
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("template", file);
      form.append("mapping", JSON.stringify(mapping));
      form.append("export_type", props.exportType);
      if (props.selectedFacultyIds.length) form.append("faculty_ids", props.selectedFacultyIds.join(","));
      if (props.year) form.append("publication_year", props.year);
      if (props.yearStart) form.append("year_start", props.yearStart);
      if (props.yearEnd) form.append("year_end", props.yearEnd);
      if (props.dateStart) form.append("date_start", props.dateStart);
      if (props.dateEnd) form.append("date_end", props.dateEnd);
      const res = await fetch(`${API_BASE}/publications/exports/template/compile`, {
        method: "POST",
        headers: authHeader(),
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Compile failed");
      }
      const blob = await res.blob();
      downloadBlob(blob, res.headers.get("content-disposition") ?? "", `publications_custom.${analysis.format}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Compile failed");
    } finally {
      setBusy(false);
    }
  }

  function rowClass(header: string): string {
    if (!analysis) return "";
    if (analysis.unknown.includes(header) && !mapping[header]) return "bg-red-50";
    if (header in analysis.suggestions || header in analysis.llm_guesses) return "bg-amber-50";
    return "";
  }

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
      <div>
        <h3 className="text-sm font-semibold text-slate-700">Custom template export</h3>
        <p className="text-xs text-slate-500 mt-1">
          Upload a CSV, Excel, or Word file whose header row lists the columns you want (in any
          order). We match each column to the data, ask you to confirm anything uncertain, then
          return the file in the same format. The filters above (faculty, year, date range) apply.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="file"
          accept=".csv,.xlsx,.xls,.docx"
          onChange={(e) => {
            setFile(e.target.files?.[0] ?? null);
            setAnalysis(null);
            setNotice("");
          }}
          className="text-sm"
        />
        <label className="text-xs text-slate-600 flex items-center gap-1">
          <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
          Use local AI for unmatched columns
        </label>
        <button
          type="button"
          disabled={!file || busy}
          onClick={analyze}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50"
        >
          {busy ? "Working…" : "Analyze template"}
        </button>
      </div>

      {notice && <p className="text-xs text-slate-600 bg-slate-50 border rounded-lg px-3 py-2">{notice}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      {analysis && (
        <div className="space-y-3">
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead className="text-left text-slate-600 border-b bg-slate-50">
                <tr>
                  <th className="py-2 px-3 font-medium">Your column</th>
                  <th className="py-2 px-3 font-medium">Maps to data field</th>
                  <th className="py-2 px-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {analysis.headers.map((header) => (
                  <tr key={header} className={`border-b border-slate-100 ${rowClass(header)}`}>
                    <td className="py-2 px-3">{header}</td>
                    <td className="py-2 px-3">
                      <select
                        className="border rounded px-2 py-1 text-sm"
                        value={mapping[header] ?? ""}
                        onChange={(e) => setMapping((m) => ({ ...m, [header]: e.target.value }))}
                      >
                        <option value="">— choose a field —</option>
                        {analysis.available_fields.map((f) => (
                          <option key={f} value={f}>
                            {f}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td className="py-2 px-3 text-xs text-slate-500">
                      {header in analysis.matched
                        ? "Matched"
                        : header in analysis.suggestions
                          ? `Guessed (${Math.round(analysis.suggestions[header].score * 100)}%) — confirm`
                          : header in analysis.llm_guesses
                            ? "AI guess — confirm"
                            : mapping[header]
                              ? "Chosen"
                              : "Not in database — pick a field"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            type="button"
            disabled={busy}
            onClick={compile}
            className="rounded-lg bg-teal-700 text-white px-4 py-2 text-sm disabled:opacity-50"
          >
            {busy ? "Compiling…" : `Compile & download (${analysis.format.toUpperCase()})`}
          </button>
        </div>
      )}
    </section>
  );
}

export default function PublicationExportsPage() {
  const [faculty, setFaculty] = useState<Faculty[]>([]);
  const [selectedFacultyIds, setSelectedFacultyIds] = useState<string[]>([]);
  const [year, setYear] = useState("");
  const [yearStart, setYearStart] = useState("");
  const [yearEnd, setYearEnd] = useState("");
  const [dateStart, setDateStart] = useState("");
  const [dateEnd, setDateEnd] = useState("");
  const [scope, setScope] = useState<"all" | "faculty" | "year">("all");
  const [exportType, setExportType] = useState<"publications" | "patents" | "both">("both");
  const [error, setError] = useState("");

  useEffect(() => {
    listFaculty({ page: 1, page_size: 200 })
      .then((r) => setFaculty(r.items))
      .catch(() => {});
  }, []);

  function buildParams(format: "csv" | "xlsx" | "pdf" | "docx") {
    const p = new URLSearchParams({ format, scope, export_type: exportType });
    if (selectedFacultyIds.length) p.set("faculty_ids", selectedFacultyIds.join(","));
    if (year) p.set("publication_year", year);
    if (yearStart) p.set("year_start", yearStart);
    if (yearEnd) p.set("year_end", yearEnd);
    if (dateStart) p.set("date_start", dateStart);
    if (dateEnd) p.set("date_end", dateEnd);
    return p;
  }

  async function runExport(format: "csv" | "xlsx" | "pdf" | "docx") {
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
        Export publications as Excel, CSV, PDF, or Word. Faculty-wise and year-wise grouping is
        supported, and you can filter by year range or exact date range. Or upload your own template
        below to get the data in your exact columns and format.
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
          <label className="text-sm">
            <span className="block text-slate-600 mb-1">Date range start</span>
            <input
              type="date"
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={dateStart}
              onChange={(e) => setDateStart(e.target.value)}
            />
          </label>
          <label className="text-sm">
            <span className="block text-slate-600 mb-1">Date range end</span>
            <input
              type="date"
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={dateEnd}
              onChange={(e) => setDateEnd(e.target.value)}
            />
          </label>
        </div>
        <p className="text-xs text-slate-500">
          Date range filters on each publication's exact date. Publications without a recorded
          date are excluded from a date-range export — run “Backfill dates” on the admin page first.
        </p>
      </section>

      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <div className="flex flex-wrap gap-3">
        {(["csv", "xlsx", "pdf", "docx"] as const).map((fmt) => (
          <button
            key={fmt}
            type="button"
            onClick={() => runExport(fmt)}
            className={`rounded-lg px-4 py-2 text-sm ${
              fmt === "csv" ? "bg-teal-700 text-white" : "border border-slate-300"
            }`}
          >
            Export {fmt === "docx" ? "WORD" : fmt.toUpperCase()}
          </button>
        ))}
      </div>

      <CustomTemplateExport
        selectedFacultyIds={selectedFacultyIds}
        exportType={exportType}
        year={year}
        yearStart={yearStart}
        yearEnd={yearEnd}
        dateStart={dateStart}
        dateEnd={dateEnd}
      />
    </div>
  );
}
