import { FormEvent, useEffect, useState } from "react";
import CoWarningsBanner from "../../components/CoWarningsBanner";
import EvalTable, { type EvalTableData } from "../../components/EvalTable";
import ComparisonSetupPanel from "../../components/ComparisonSetupPanel";
import EvaluationScopePanel from "../../components/EvaluationScopePanel";
import FileUploadField from "../../components/FileUploadField";
import CourseSearchSelect from "../../components/CourseSearchSelect";
import { useMarksFileParse } from "../../hooks/useMarksFileParse";
import type { ComparisonSetup, MarksParsePreview } from "../../types/copo";
import { apiGet, apiPostForm } from "../../services/api";

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

export default function CopoComparePage() {
  const [courses, setCourses] = useState<string[]>([]);
  const [mappingMode, setMappingMode] = useState<"default" | "custom">("default");
  const [customMapping, setCustomMapping] = useState<File | null>(null);
  const [courseTitle, setCourseTitle] = useState("");
  const [marksFile, setMarksFile] = useState<File | null>(null);
  const [compareFile, setCompareFile] = useState<File | null>(null);
  const [uploadId, setUploadId] = useState<number | null>(null);
  const [parsePreview, setParsePreview] = useState<MarksParsePreview | null>(null);
  const [programmes, setProgrammes] = useState<string[]>([]);
  const [branches, setBranches] = useState<string[]>([]);
  const [coCell, setCoCell] = useState("");
  const [poCell, setPoCell] = useState("");
  const [coTable, setCoTable] = useState<EvalTableData | null>(null);
  const [poTable, setPoTable] = useState<EvalTableData | null>(null);
  const [comparisonSetup, setComparisonSetup] = useState<ComparisonSetup | null>(null);
  const [coWarnings, setCoWarnings] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const { parseMarksFile, parsing, error: parseError, setError: setParseError } = useMarksFileParse();

  useEffect(() => {
    apiGet<{ courses: string[] }>("/copo/course-names")
      .then((r) => setCourses(r.courses))
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load courses"));
  }, []);

  useEffect(() => {
    if (!marksFile) {
      setParsePreview(null);
      setUploadId(null);
      setProgrammes([]);
      setBranches([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setParseError("");
      const preview = await parseMarksFile(marksFile, courseTitle);
      if (cancelled || !preview) return;
      setParsePreview(preview);
      setUploadId(preview.upload_id);
      const defaults = defaultScopeFromPreview(preview);
      setProgrammes(defaults.programmes);
      setBranches(defaults.branches);
    })();
    return () => {
      cancelled = true;
    };
  }, [marksFile, courseTitle, parseMarksFile, setParseError]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!uploadId || !compareFile || !courseTitle) return;
    setError("");
    setBusy(true);
    setCoTable(null);
    setPoTable(null);
    setComparisonSetup(null);
    setCoWarnings([]);
    const fd = new FormData();
    fd.append("course_title", courseTitle);
    fd.append("upload_id", String(uploadId));
    fd.append("compare_file", compareFile);
    fd.append("mapping_option", mappingMode === "default" ? "default" : "upload");
    if (mappingMode === "custom" && customMapping) {
      fd.append("mapping_file", customMapping);
    }
    programmes.forEach((p) => fd.append("programmes", p));
    branches.forEach((b) => fd.append("branches", b));
    fd.append("co_attainment_cell", coCell);
    fd.append("po_attainment_cell", poCell);
    try {
      const r = await apiPostForm<{
        co_table: EvalTableData;
        po_table: EvalTableData;
        comparison_setup?: ComparisonSetup;
        co_warnings?: string[];
      }>("/copo/evaluate/compare", fd);
      setCoTable(r.co_table);
      setPoTable(r.po_table);
      setComparisonSetup(r.comparison_setup ?? null);
      setCoWarnings(r.co_warnings ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Compare failed");
    } finally {
      setBusy(false);
    }
  }

  const displayError = error || parseError;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Single Course — Compare Evaluation</h2>
      <p className="text-sm text-slate-600">
        Validates calculated CO/PO values against a reference Excel (optional cell overrides).
      </p>
      {displayError && (
        <p className="text-sm text-red-700 bg-red-50 rounded px-3 py-2 whitespace-pre-wrap">
          {displayError}
        </p>
      )}

      <form onSubmit={onSubmit} className="space-y-6">
        <section className="bg-white border rounded-xl p-6 space-y-4">
          <div className="flex flex-wrap gap-4 text-sm">
            <label className="flex items-center gap-1">
              <input
                type="radio"
                checked={mappingMode === "default"}
                onChange={() => setMappingMode("default")}
              />
              Default mapping
            </label>
            <label className="flex items-center gap-1">
              <input
                type="radio"
                checked={mappingMode === "custom"}
                onChange={() => setMappingMode("custom")}
              />
              Custom mapping
            </label>
          </div>
          {mappingMode === "custom" && (
            <FileUploadField
              label="Custom mapping Excel"
              file={customMapping}
              onFileChange={setCustomMapping}
            />
          )}

          <CourseSearchSelect
            courses={courses}
            value={courseTitle}
            onChange={setCourseTitle}
            placeholder="Search by course code or name…"
            required
          />

          <FileUploadField
            label="Consolidated marks Excel"
            file={marksFile}
            onFileChange={(f) => {
              setMarksFile(f);
              setParsePreview(null);
              setUploadId(null);
            }}
          />
          {parsing && <p className="text-sm text-slate-600">Analyzing file…</p>}
          {parsePreview && !parsing && (
            <p className="text-sm text-green-800">✓ File analyzed successfully</p>
          )}

          <FileUploadField
            label="Comparison Excel (expected output)"
            file={compareFile}
            onFileChange={setCompareFile}
          />

          <div className="grid sm:grid-cols-2 gap-3">
            <label className="text-sm">
              CO attainment cell override (optional)
              <input
                value={coCell}
                onChange={(e) => setCoCell(e.target.value)}
                placeholder="e.g. B45"
                className="mt-1 w-full border rounded px-2 py-1"
              />
            </label>
            <label className="text-sm">
              PO attainment cell override (optional)
              <input
                value={poCell}
                onChange={(e) => setPoCell(e.target.value)}
                placeholder="e.g. B50"
                className="mt-1 w-full border rounded px-2 py-1"
              />
            </label>
          </div>
        </section>

        {parsePreview && (
          <EvaluationScopePanel
            preview={parsePreview}
            programmes={programmes}
            branches={branches}
            onProgrammesChange={setProgrammes}
            onBranchesChange={setBranches}
          />
        )}

        <button
          type="submit"
          disabled={busy || !uploadId || !compareFile || !courseTitle || parsing}
          className="w-full rounded-lg bg-teal-700 text-white py-3 font-semibold disabled:opacity-50"
        >
          {busy ? "Comparing…" : "Compare output"}
        </button>
      </form>

      {comparisonSetup && (
        <>
          <CoWarningsBanner warnings={coWarnings} />
          <ComparisonSetupPanel setup={comparisonSetup} />
          {coTable && <EvalTable table={coTable} />}
          {poTable && <EvalTable table={poTable} />}
        </>
      )}
    </div>
  );
}
