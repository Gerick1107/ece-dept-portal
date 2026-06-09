import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import CoWarningsBanner from "../../components/CoWarningsBanner";
import ConstraintMarksTemplatePanel from "../../components/ConstraintMarksTemplatePanel";
import CopoFullResultsView from "../../components/CopoFullResultsView";
import CopoAttainmentCharts from "../analytics/components/CopoAttainmentCharts";
import EvaluationScopePanel from "../../components/EvaluationScopePanel";
import FileUploadField from "../../components/FileUploadField";
import CourseSearchSelect from "../../components/CourseSearchSelect";
import { useAuth } from "../auth/AuthContext";
import { createCourse, listCourses } from "../shared/portalApi";
import { useMarksFileParse } from "../../hooks/useMarksFileParse";
import type { MarksParsePreview } from "../../types/copo";
import { apiGet, apiPostForm, downloadCopoFile } from "../../services/api";

type EvalResult = {
  public_id: string;
  course_title: string;
  course_filename?: string;
  mapping_filename?: string;
  scope_summary?: string;
  unique_COs: string[];
  intermediate: Record<string, unknown>;
  co_warnings?: string[];
  download_token?: string;
  download_filename?: string;
  data_deleted?: boolean;
  ephemeral?: boolean;
};

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

export default function CopoEvaluatePage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [courses, setCourses] = useState<string[]>([]);
  const [courseTitle, setCourseTitle] = useState("");
  const [mappingMode, setMappingMode] = useState<"default" | "custom">("default");
  const [customMappingFile, setCustomMappingFile] = useState<File | null>(null);
  const [marksFile, setMarksFile] = useState<File | null>(null);
  const [programmes, setProgrammes] = useState<string[]>([]);
  const [branches, setBranches] = useState<string[]>([]);
  const [parsePreview, setParsePreview] = useState<MarksParsePreview | null>(null);
  const [indirect, setIndirect] = useState<Record<string, string>>({});
  const [removeMarksAfter, setRemoveMarksAfter] = useState(false);
  const [skipDatabaseSave, setSkipDatabaseSave] = useState(false);
  const [previewUploadId, setPreviewUploadId] = useState(0);
  const [result, setResult] = useState<EvalResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showAddCourse, setShowAddCourse] = useState(false);
  const [newCourseCode, setNewCourseCode] = useState("");
  const [newCourseName, setNewCourseName] = useState("");
  const [courseMessage, setCourseMessage] = useState("");
  const [semesterTerm, setSemesterTerm] = useState<"Monsoon" | "Winter" | "Summer">("Monsoon");
  const [semesterYear, setSemesterYear] = useState(String(new Date().getFullYear()));
  const { parseMarksFile, parsing, error: parseError, setError: setParseError } = useMarksFileParse();

  const loadCourses = useCallback(async (mappingFile?: File) => {
    try {
      if (mappingFile) {
        const fd = new FormData();
        fd.append("mapping_file", mappingFile);
        const r = await apiPostForm<{ courses: string[] }>("/copo/course-names", fd);
        setCourses(r.courses);
      } else {
        try {
          const db = await listCourses();
          if (db.courses.length) {
            setCourses(db.courses.map((c) => c.label));
            return;
          }
        } catch {
          /* fall through to mapping file */
        }
        const r = await apiGet<{ courses: string[] }>("/copo/course-names");
        setCourses(r.courses);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load courses");
      setCourses([]);
    }
  }, []);

  useEffect(() => {
    loadCourses();
  }, [loadCourses]);

  useEffect(() => {
    if (!courseTitle) return;
    const fd = new FormData();
    fd.append("course_title", courseTitle);
    fd.append("mapping_option", mappingMode === "default" ? "default" : "upload");
    if (mappingMode === "custom" && customMappingFile) {
      fd.append("mapping_file", customMappingFile);
    }
    apiPostForm<{ cos: string[]; indirect_values: Record<string, number> }>("/copo/course-cos", fd)
      .then((r) => {
        const init: Record<string, string> = {};
        r.cos.forEach((co) => {
          init[co] = r.indirect_values[co] != null ? String(r.indirect_values[co]) : "";
        });
        setIndirect(init);
      })
      .catch(() => setIndirect({}));
  }, [courseTitle, mappingMode, customMappingFile]);

  // Auto-parse marks file on upload (legacy portal behaviour).
  useEffect(() => {
    if (!marksFile) {
      setParsePreview(null);
      setProgrammes([]);
      setBranches([]);
      return;
    }
    let cancelled = false;
    (async () => {
      setParseError("");
      const preview = await parseMarksFile(marksFile, courseTitle, { persist: false });
      if (cancelled || !preview) return;
      setParsePreview(preview);
      setPreviewUploadId(preview.upload_id || 0);
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
    if (!marksFile || !courseTitle) return;
    setError("");
    setBusy(true);
    setResult(null);
    const fd = new FormData();
    fd.append("course_title", courseTitle);
    fd.append("course_file", marksFile);
    fd.append("use_default_mapping", mappingMode === "default" ? "true" : "false");
    if (mappingMode === "custom" && customMappingFile) {
      fd.append("mapping_file", customMappingFile);
    }
    programmes.forEach((p) => fd.append("programmes", p));
    branches.forEach((b) => fd.append("branches", b));
    const indirectNums: Record<string, number> = {};
    Object.entries(indirect).forEach(([co, v]) => {
      if (v.trim()) indirectNums[co] = parseFloat(v);
    });
    fd.append("indirect_attainment_json", JSON.stringify(indirectNums));
    fd.append("remove_marks_after", removeMarksAfter ? "true" : "false");
    fd.append("skip_database_save", skipDatabaseSave ? "true" : "false");
    if (previewUploadId) fd.append("preview_upload_id", String(previewUploadId));
    fd.append("semester_term", semesterTerm);
    fd.append("semester_year", semesterYear);

    try {
      const r = await apiPostForm<EvalResult>("/copo/final-submit", fd);
      setResult(r);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed");
    } finally {
      setBusy(false);
    }
  }

  const displayError = error || parseError;

  return (
    <div className="space-y-6">
      <div className="bg-teal-50 border border-teal-200 rounded-xl p-4 text-sm text-teal-900">
        Upload <strong>one consolidated Excel</strong> for the course with all assessment columns
        (quizzes, midsem, endsem, etc.) for the semester.
        <a href="/api/v1/copo/template" className="ml-2 underline font-medium" download>
          Download sample template
        </a>
      </div>

      <ConstraintMarksTemplatePanel initialCourseCode={courseTitle} />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold">Generate CO-PO Attainment Report</h2>
        {isAdmin && (
          <button
            type="button"
            className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm"
            onClick={() => {
              setNewCourseCode("");
              setNewCourseName("");
              setCourseMessage("");
              setShowAddCourse(true);
            }}
          >
            Add Course
          </button>
        )}
      </div>
      {displayError && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2 whitespace-pre-wrap">
          {displayError}
        </p>
      )}

      <form onSubmit={onSubmit} className="space-y-6">
        <section className="bg-white border rounded-xl p-6 space-y-4">
          <h3 className="font-medium flex items-center gap-2">
            <span className="bg-teal-700 text-white w-6 h-6 rounded-full text-xs flex items-center justify-center">
              1
            </span>
            Select course
          </h3>
          <CourseSearchSelect
            courses={courses}
            value={courseTitle}
            onChange={setCourseTitle}
            placeholder="Search by course code or name…"
            required
          />
        </section>

        <section className="bg-white border rounded-xl p-6 space-y-4">
          <h3 className="font-medium flex items-center gap-2">
            <span className="bg-teal-700 text-white w-6 h-6 rounded-full text-xs flex items-center justify-center">
              2
            </span>
            CO-PO mapping (department file)
          </h3>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={mappingMode === "default"}
              onChange={() => {
                setMappingMode("default");
                loadCourses();
              }}
            />
            Default department mapping
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" checked={mappingMode === "custom"} onChange={() => setMappingMode("custom")} />
            Custom mapping file
          </label>
          {mappingMode === "custom" && (
            <FileUploadField
              label="Mapping Excel"
              file={customMappingFile}
              onFileChange={async (f) => {
                setCustomMappingFile(f);
                if (f) await loadCourses(f);
              }}
            />
          )}
        </section>

        <section className="bg-white border rounded-xl p-6 space-y-4">
          <h3 className="font-medium flex items-center gap-2">
            <span className="bg-teal-700 text-white w-6 h-6 rounded-full text-xs flex items-center justify-center">
              3
            </span>
            Semester &amp; consolidated marks file
          </h3>
          <div className="grid sm:grid-cols-2 gap-3 max-w-md">
            <div>
              <label className="text-xs text-slate-500">Semester</label>
              <select
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
                value={semesterTerm}
                onChange={(e) => setSemesterTerm(e.target.value as "Monsoon" | "Winter" | "Summer")}
              >
                <option value="Monsoon">Monsoon</option>
                <option value="Winter">Winter</option>
                <option value="Summer">Summer</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Year</label>
              <input
                className="w-full border rounded-lg px-3 py-2 text-sm mt-1"
                value={semesterYear}
                onChange={(e) => setSemesterYear(e.target.value)}
                placeholder="2025"
              />
            </div>
          </div>
          <FileUploadField
            label="End-of-semester student marks (.xlsx)"
            file={marksFile}
            onFileChange={(f) => {
              setMarksFile(f);
              setParsePreview(null);
              setResult(null);
            }}
            hint="Single file with ALL assessments as columns — see template."
          />
          {parsing && <p className="text-sm text-slate-600">Analyzing file…</p>}
          {parsePreview && !parsing && (
            <p className="text-sm text-green-800 flex items-center gap-1">
              <span aria-hidden>✓</span> {parsePreview.parse_message ?? "File analyzed successfully"}
            </p>
          )}
        </section>

        {parsePreview && (
          <EvaluationScopePanel
            preview={parsePreview}
            programmes={programmes}
            branches={branches}
            onProgrammesChange={setProgrammes}
            onBranchesChange={setBranches}
            stepNumber={4}
          />
        )}

        {Object.keys(indirect).length > 0 && (
          <section className="bg-white border rounded-xl p-6">
            <h3 className="font-medium mb-2 flex items-center gap-2">
              <span className="bg-teal-700 text-white w-6 h-6 rounded-full text-xs flex items-center justify-center">
                5
              </span>
              Indirect CO attainment (optional, 0–100)
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {Object.keys(indirect).map((co) => (
                <label key={co} className="text-xs">
                  {co}
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    max={100}
                    value={indirect[co]}
                    onChange={(e) => setIndirect({ ...indirect, [co]: e.target.value })}
                    className="mt-0.5 w-full border rounded px-2 py-1"
                  />
                </label>
              ))}
            </div>
          </section>
        )}

        <section className="bg-white border rounded-xl p-6 space-y-3">
          <p className="text-xs text-slate-600">
            Note: Final PO/PSO attainment = 90% Direct + 10% Indirect. Only students from selected
            programmes/branches are included in computation.
          </p>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={skipDatabaseSave}
              onChange={(e) => setSkipDatabaseSave(e.target.checked)}
            />
            <span>
              Do not save this run to the database (results stay in this browser session only;
              download the Excel before leaving the page).
            </span>
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              className="mt-1"
              checked={removeMarksAfter}
              onChange={(e) => setRemoveMarksAfter(e.target.checked)}
            />
            <span>
              Delete all server data after successful processing — both marks upload rows, the
              evaluation run, generated Excel, and any archives (same as the manual delete button).
              Download your report first if you need a copy.
            </span>
          </label>
          <button
            type="submit"
            disabled={!marksFile || !courseTitle || busy || parsing}
            className="w-full rounded-lg bg-teal-700 text-white py-3 font-semibold disabled:opacity-50"
          >
            {busy ? "Processing consolidated file…" : "Generate CO-PO results"}
          </button>
        </section>
      </form>

      {result && (
        <section className="space-y-4">
          <div className="flex flex-wrap gap-2 justify-between items-center">
            <h3 className="text-lg font-semibold">Results — {result.course_title}</h3>
            <div className="flex flex-wrap gap-2">
              {result.download_token && (
                <button
                  type="button"
                  onClick={() =>
                    downloadCopoFile(
                      result.download_token!,
                      result.download_filename || `${result.course_title}_CO_PO_Percentage_Results.xlsx`
                    )
                  }
                  className="rounded-lg bg-green-700 text-white px-4 py-2 text-sm hover:bg-green-800"
                >
                  Download Excel
                </button>
              )}
              {result.public_id && !result.data_deleted && !result.ephemeral && (
                <Link
                  to={`/copo/results/${result.public_id}`}
                  className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50"
                >
                  Open saved results
                </Link>
              )}
            </div>
          </div>
          <CoWarningsBanner warnings={result.co_warnings ?? []} />
          {result.public_id && <CopoAttainmentCharts publicId={result.public_id} />}
          <CopoFullResultsView
            courseTitle={result.course_title}
            courseFilename={result.course_filename}
            mappingFilename={result.mapping_filename}
            uniqueCos={result.unique_COs}
            intermediate={result.intermediate}
            scopeSummary={result.scope_summary}
          />
        </section>
      )}

      {showAddCourse && isAdmin && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3">
            <h3 className="font-semibold">Add course</h3>
            {courseMessage && (
              <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded px-3 py-2">{courseMessage}</p>
            )}
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Course code"
              value={newCourseCode}
              onChange={(e) => setNewCourseCode(e.target.value)}
            />
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Course name"
              value={newCourseName}
              onChange={(e) => setNewCourseName(e.target.value)}
            />
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowAddCourse(false)}>
                Cancel
              </button>
              <button
                type="button"
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg"
                onClick={async () => {
                  try {
                    await createCourse(newCourseCode, newCourseName);
                    setCourseMessage("Course added successfully.");
                    await loadCourses();
                    setTimeout(() => setShowAddCourse(false), 800);
                  } catch (e) {
                    setCourseMessage("");
                    setError(e instanceof Error ? e.message : "Could not add course");
                  }
                }}
              >
                Submit
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
