import { FormEvent, useCallback, useEffect, useState } from "react";
import CoWarningsBanner from "../../components/CoWarningsBanner";
import EvalTable, { type EvalTableData } from "../../components/EvalTable";
import BulkScopeMultiSelect from "../../components/BulkScopeMultiSelect";
import ComparisonSetupPanel from "../../components/ComparisonSetupPanel";
import FileUploadField from "../../components/FileUploadField";
import CourseSearchSelect from "../../components/CourseSearchSelect";
import { useMarksFileParse } from "../../hooks/useMarksFileParse";
import type { ComparisonSetup, MarksParsePreview } from "../../types/copo";
import { apiGet, apiPostForm } from "../../services/api";

type BulkRow = {
  id: string;
  courseTitle: string;
  marksFile: File | null;
  uploadId: number | null;
  parsePreview: MarksParsePreview | null;
  programmes: string[];
  branches: string[];
  compareFile: File | null;
  coCell: string;
  poCell: string;
  parseStatus: string;
};

type BulkResult = {
  status: string;
  row_number: number;
  course_title?: string;
  course_filename?: string;
  compare_filename?: string;
  mapping_filename?: string;
  scope_summary?: string;
  error_message?: string;
  failed_file?: string;
  co_warnings?: string[];
  co_table?: EvalTableData;
  po_table?: EvalTableData;
};

function newRow(id: string): BulkRow {
  return {
    id,
    courseTitle: "",
    marksFile: null,
    uploadId: null,
    parsePreview: null,
    programmes: [],
    branches: [],
    compareFile: null,
    coCell: "",
    poCell: "",
    parseStatus: "",
  };
}

function defaultScopeFromPreview(preview: MarksParsePreview) {
  return {
    programmes: preview.default_programmes.length
      ? preview.default_programmes
      : Object.keys(preview.programmes),
    branches: preview.default_branches.length
      ? preview.default_branches
      : Object.keys(preview.branches),
  };
}

function formatBulkStatus(preview: MarksParsePreview): string {
  const progParts = Object.entries(preview.programmes).map(([k, c]) => `${k} (${c})`);
  const base = `Ready: ${preview.total_students} students, ${preview.cos.length} COs`;
  return progParts.length ? `${base} · ${progParts.join(", ")}` : base;
}

export default function CopoBulkPage() {
  const [courses, setCourses] = useState<string[]>([]);
  const [mappingMode, setMappingMode] = useState<"default" | "custom">("default");
  const [customMapping, setCustomMapping] = useState<File | null>(null);
  const [rows, setRows] = useState<BulkRow[]>([newRow("1"), newRow("2")]);
  const [results, setResults] = useState<BulkResult[] | null>(null);
  const [mappingFilename, setMappingFilename] = useState("");
  const [summary, setSummary] = useState({ total: 0, success: 0, error: 0 });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { parseMarksFile } = useMarksFileParse();

  const loadCourses = useCallback(async () => {
    try {
      const r = await apiGet<{ courses: string[] }>("/copo/course-names");
      setCourses(r.courses);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load courses");
    }
  }, []);

  useEffect(() => {
    loadCourses();
  }, [loadCourses]);

  function updateRow(id: string, patch: Partial<BulkRow>) {
    setRows((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  function addRow() {
    setRows((prev) => [...prev, newRow(String(Date.now()))]);
  }

  function removeRow(id: string) {
    setRows((prev) => (prev.length <= 1 ? prev : prev.filter((r) => r.id !== id)));
  }

  async function autoParseRow(row: BulkRow, file: File) {
    updateRow(row.id, { parseStatus: "Parsing…", marksFile: file });
    const preview = await parseMarksFile(file, row.courseTitle);
    if (!preview) {
      updateRow(row.id, {
        parseStatus: "Parse failed",
        uploadId: null,
        parsePreview: null,
        programmes: [],
        branches: [],
      });
      return;
    }
    const defaults = defaultScopeFromPreview(preview);
    updateRow(row.id, {
      uploadId: preview.upload_id,
      parsePreview: preview,
      programmes: defaults.programmes,
      branches: defaults.branches,
      parseStatus: formatBulkStatus(preview),
    });
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    setResults(null);

    const activeRows = rows.filter((r) => r.courseTitle && r.uploadId && r.compareFile);
    if (!activeRows.length) {
      setError("Fill at least one row with course, parsed marks, and comparison file.");
      setBusy(false);
      return;
    }

    const fd = new FormData();
    fd.append("use_default_mapping", mappingMode === "default" ? "true" : "false");
    if (mappingMode === "custom" && customMapping) {
      fd.append("mapping_file", customMapping);
    }
    fd.append(
      "rows_json",
      JSON.stringify(
        activeRows.map((r) => ({
          course_title: r.courseTitle,
          upload_id: r.uploadId,
          programmes: r.programmes,
          branches: r.branches,
          co_cell: r.coCell,
          po_cell: r.poCell,
        }))
      )
    );
    activeRows.forEach((r) => {
      if (r.compareFile) fd.append("compare_files", r.compareFile);
    });

    try {
      const r = await apiPostForm<{
        results: BulkResult[];
        mapping_filename: string;
        total_rows: number;
        success_count: number;
        error_count: number;
      }>("/copo/evaluate/bulk", fd);
      setResults(r.results);
      setMappingFilename(r.mapping_filename);
      setSummary({
        total: r.total_rows,
        success: r.success_count,
        error: r.error_count,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk evaluation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Bulk Compare Multiple Courses</h2>
        <p className="text-sm text-slate-600 mt-1">
          Compare calculated attainment vs reference Excel per course. Each row uses one consolidated
          marks file. Failures are isolated per row.
        </p>
      </div>
      {error && (
        <p className="text-sm text-red-700 bg-red-50 rounded px-3 py-2 whitespace-pre-wrap">{error}</p>
      )}

      <section className="bg-white border rounded-xl p-4 space-y-3 text-sm">
        <span className="font-medium">CO-PO mapping (shared for all rows)</span>
        <div className="flex flex-wrap gap-4 items-center">
          <label className="flex items-center gap-1">
            <input
              type="radio"
              checked={mappingMode === "default"}
              onChange={() => setMappingMode("default")}
            />
            Use default for all rows
          </label>
          <label className="flex items-center gap-1">
            <input
              type="radio"
              checked={mappingMode === "custom"}
              onChange={() => setMappingMode("custom")}
            />
            Upload one custom mapping for all rows
          </label>
        </div>
        {mappingMode === "custom" && (
          <FileUploadField
            label="Custom mapping Excel"
            file={customMapping}
            onFileChange={setCustomMapping}
          />
        )}
      </section>

      <form onSubmit={onSubmit} className="space-y-4">
        <div className="bg-teal-50 border border-teal-100 rounded-lg px-4 py-2 text-xs text-teal-900">
          Upload an input sheet per row to auto-detect programmes, branches, and COs. Programme and
          branch columns support multi-select (Ctrl/Cmd+click).
        </div>
        <div className="overflow-x-auto border rounded-xl bg-white">
          <table className="min-w-[1200px] w-full text-sm">
            <thead>
              <tr className="bg-slate-800 text-white text-left text-xs uppercase">
                <th className="p-2 w-8">#</th>
                <th className="p-2 min-w-[200px]">Input sheet</th>
                <th className="p-2 min-w-[180px]">To compare with</th>
                <th className="p-2 min-w-[200px]">Course</th>
                <th className="p-2 min-w-[140px]">Programme</th>
                <th className="p-2 min-w-[140px]">Branch</th>
                <th className="p-2 w-24">CO cell</th>
                <th className="p-2 w-24">PO cell</th>
                <th className="p-2 min-w-[160px]">Status</th>
                <th className="p-2 w-16"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr key={row.id} className="border-t align-top">
                  <td className="p-2 font-medium">{idx + 1}</td>
                  <td className="p-2">
                    <FileUploadField
                      label=""
                      file={row.marksFile}
                      onFileChange={(f) => {
                        if (!f) {
                          updateRow(row.id, {
                            marksFile: null,
                            uploadId: null,
                            parsePreview: null,
                            parseStatus: "",
                            programmes: [],
                            branches: [],
                          });
                          return;
                        }
                        void autoParseRow(row, f);
                      }}
                    />
                  </td>
                  <td className="p-2">
                    <FileUploadField
                      label=""
                      file={row.compareFile}
                      onFileChange={(f) => updateRow(row.id, { compareFile: f })}
                    />
                  </td>
                  <td className="p-2">
                    <CourseSearchSelect
                      courses={courses}
                      value={row.courseTitle}
                      onChange={(v) => updateRow(row.id, { courseTitle: v })}
                      placeholder="Search course…"
                      className="w-full border rounded px-2 py-1 text-sm"
                    />
                  </td>
                  <td className="p-2">
                    <BulkScopeMultiSelect
                      column="programme"
                      preview={row.parsePreview}
                      programmes={row.programmes}
                      branches={row.branches}
                      onProgrammesChange={(p) => updateRow(row.id, { programmes: p })}
                      onBranchesChange={(b) => updateRow(row.id, { branches: b })}
                    />
                  </td>
                  <td className="p-2">
                    <BulkScopeMultiSelect
                      column="branch"
                      preview={row.parsePreview}
                      programmes={row.programmes}
                      branches={row.branches}
                      onProgrammesChange={(p) => updateRow(row.id, { programmes: p })}
                      onBranchesChange={(b) => updateRow(row.id, { branches: b })}
                    />
                  </td>
                  <td className="p-2">
                    <input
                      value={row.coCell}
                      onChange={(e) => updateRow(row.id, { coCell: e.target.value })}
                      placeholder="Label/value"
                      className="w-full border rounded px-2 py-1 text-xs"
                    />
                  </td>
                  <td className="p-2">
                    <input
                      value={row.poCell}
                      onChange={(e) => updateRow(row.id, { poCell: e.target.value })}
                      placeholder="Label/value"
                      className="w-full border rounded px-2 py-1 text-xs"
                    />
                  </td>
                  <td className="p-2 text-xs text-green-700 whitespace-pre-wrap">{row.parseStatus}</td>
                  <td className="p-2">
                    <button
                      type="button"
                      onClick={() => removeRow(row.id)}
                      className="text-red-600 text-xs"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="flex gap-3">
          <button type="button" onClick={addRow} className="rounded border px-4 py-2 text-sm">
            Add another course
          </button>
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-teal-700 text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {busy ? "Running bulk evaluation…" : "Run bulk evaluation"}
          </button>
        </div>
      </form>

      {results && (
        <section className="space-y-6">
          <h3 className="text-lg font-semibold">Bulk evaluation results</h3>
          <p className="text-sm text-slate-600">
            Each row was executed independently. Failures are isolated so one bad workbook does not
            stop the rest.
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              ["Rows processed", summary.total],
              ["Successful", summary.success],
              ["Failed", summary.error],
              ["Mapping file", mappingFilename || "—"],
            ].map(([label, val]) => (
              <div key={String(label)} className="bg-white border rounded-xl p-4 text-center">
                <p className="text-xs uppercase text-slate-500 font-semibold">{label}</p>
                <p className="text-lg font-semibold mt-1 truncate" title={String(val)}>
                  {val}
                </p>
              </div>
            ))}
          </div>

          <div className="overflow-x-auto border rounded-xl bg-white">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="bg-slate-800 text-white text-xs uppercase">
                  <th className="p-2">Row</th>
                  <th className="p-2">Input sheet</th>
                  <th className="p-2">To compare with</th>
                  <th className="p-2">Course</th>
                  <th className="p-2">Status</th>
                  <th className="p-2">Failed file</th>
                  <th className="p-2">Details</th>
                </tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.row_number} className="border-t">
                    <td className="p-2">{r.row_number}</td>
                    <td className="p-2">{r.course_filename ?? "—"}</td>
                    <td className="p-2">{r.compare_filename ?? "—"}</td>
                    <td className="p-2">{r.course_title ?? "—"}</td>
                    <td
                      className={`p-2 font-semibold ${
                        r.status === "success" ? "text-green-700" : "text-red-700"
                      }`}
                    >
                      {r.status.toUpperCase()}
                    </td>
                    <td className="p-2 text-xs">{r.failed_file ?? "—"}</td>
                    <td className="p-2 text-xs">
                      {r.status === "success"
                        ? "Comparison tables generated."
                        : r.error_message ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {results
            .filter((r) => r.status === "success")
            .map((r) => {
              const setup: ComparisonSetup = {
                input_sheet: r.course_filename ?? "",
                compare_filename: r.compare_filename ?? "",
                mapping_filename: r.mapping_filename ?? mappingFilename,
                scope_summary: r.scope_summary ?? "",
                threshold_rule: "max(50, Mean - 0.5*Std)",
              };
              return (
                <div key={r.row_number} className="space-y-4 border-t pt-6">
                  <h4 className="font-semibold text-teal-800">
                    Row {r.row_number} — {r.course_title}
                  </h4>
                  <p className="text-sm text-green-800 bg-green-50 rounded px-3 py-2">
                    This row finished successfully. Delta is shown as Calculated − Read.
                  </p>
                  <CoWarningsBanner warnings={r.co_warnings ?? []} />
                  <ComparisonSetupPanel setup={setup} />
                  {r.co_table && <EvalTable table={r.co_table} />}
                  {r.po_table && <EvalTable table={r.po_table} />}
                </div>
              );
            })}
        </section>
      )}
    </div>
  );
}
