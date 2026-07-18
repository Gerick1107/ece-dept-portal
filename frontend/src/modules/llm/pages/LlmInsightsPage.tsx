import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import LlmComparisonVisuals from "../components/LlmComparisonVisuals";
import ProviderSelector from "../components/ProviderSelector";
import { useLlmProvider } from "../hooks/useLlmProvider";
import {
  fetchCachedInsights,
  fetchCourseComparison,
  fetchInsightCourses,
  generateLlmInsights,
  type CourseComparison,
  type InsightCourseOption,
} from "../services/llmInsightsApi";

function trendClass(trend: string) {
  if (trend === "down") return "border-l-4 border-l-red-400 bg-red-50/60";
  if (trend === "up") return "border-l-4 border-l-emerald-400 bg-emerald-50/60";
  return "";
}

function formatDelta(delta: number | null) {
  if (delta == null) return "—";
  const sign = delta > 0 ? "▲" : delta < 0 ? "▼" : "•";
  return `${sign} ${delta > 0 ? "+" : ""}${delta.toFixed(1)}%`;
}

function InsightsBody({ text }: { text: string }) {
  return (
    <div className="prose prose-sm max-w-none text-slate-700 space-y-1.5">
      {text.split("\n").map((line, i) => {
        const trimmed = line.trim();
        if (!trimmed) return <div key={i} className="h-2" />;
        if (trimmed.startsWith("## ")) {
          return (
            <h3 key={i} className="font-semibold text-slate-800 mt-4 mb-1 text-base">
              {trimmed.slice(3)}
            </h3>
          );
        }
        if (trimmed.startsWith("# ")) {
          return (
            <h2 key={i} className="font-bold text-slate-900 mt-4 mb-1 text-lg">
              {trimmed.slice(2)}
            </h2>
          );
        }
        const parts = line.split(/(\*\*[^*]+\*\*)/g);
        return (
          <p key={i} className="text-sm leading-relaxed m-0">
            {parts.map((part, j) =>
              part.startsWith("**") && part.endsWith("**") ? (
                <strong key={j}>{part.slice(2, -2)}</strong>
              ) : (
                <span key={j}>{part}</span>
              )
            )}
          </p>
        );
      })}
    </div>
  );
}

function ComparisonTable({
  title,
  rows,
  previousLabel,
  currentLabel,
}: {
  title: string;
  rows: CourseComparison["co_comparison"];
  previousLabel: string;
  currentLabel: string;
}) {
  if (!rows.length) {
    return <p className="text-sm text-slate-500">No {title.toLowerCase()} data available.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <h4 className="text-sm font-semibold text-slate-700 mb-2">{title}</h4>
      <table className="w-full text-sm border border-slate-200 rounded-lg overflow-hidden">
        <thead>
          <tr className="bg-slate-50 text-slate-600 text-left">
            <th className="px-3 py-2 font-medium">Metric</th>
            <th className="px-3 py-2 font-medium">{previousLabel}</th>
            <th className="px-3 py-2 font-medium">{currentLabel}</th>
            <th className="px-3 py-2 font-medium">Δ Change</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.metric} className={`border-t border-slate-100 ${trendClass(row.trend)}`}>
              <td className="px-3 py-2 font-medium">{row.metric}</td>
              <td className="px-3 py-2">{row.previous != null ? `${row.previous.toFixed(1)}%` : "—"}</td>
              <td className="px-3 py-2">{row.current != null ? `${row.current.toFixed(1)}%` : "—"}</td>
              <td className="px-3 py-2">{formatDelta(row.delta)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function formatAssessmentSummary(items: CourseComparison["assessment_summary"]) {
  if (!items.length) return "No assessment structure recorded.";
  return items
    .map(
      (item) =>
        `${item.component_type}: ${item.component_count} component(s), ${item.total_questions} question column(s)`
    )
    .join("; ");
}

function AssessmentStructurePanel({
  comparison,
  previousLabel,
  currentLabel,
}: {
  comparison: CourseComparison;
  previousLabel: string;
  currentLabel: string;
}) {
  const hasCurrent =
    comparison.current_assessment_data_available ??
    (comparison.current_assessments.length > 0 || comparison.assessment_summary.length > 0);
  const hasPrevious =
    comparison.previous_assessment_data_available ??
    (comparison.previous_assessments.length > 0 || comparison.previous_assessment_summary.length > 0);

  if (!hasCurrent && !hasPrevious && comparison.has_previous) {
    return (
      <section className="bg-amber-50 border border-amber-200 rounded-xl p-4 shadow-sm">
        <h3 className="font-semibold text-amber-900">Assessment structure</h3>
        <p className="text-sm text-amber-800 mt-1">
          Neither semester has stored assessment IDs — insights will use CO/PO attainment only and will
          not invent assessment components.
        </p>
      </section>
    );
  }

  if (!hasCurrent && !hasPrevious) return null;

  function renderAssessments(assessments: CourseComparison["current_assessments"]) {
    if (!assessments.length) return <p className="text-sm text-slate-500">No per-assessment CO mapping available.</p>;
    return (
      <ul className="space-y-2 text-sm">
        {assessments.map((item) => (
          <li key={item.name} className="border border-slate-100 rounded-lg px-3 py-2 bg-slate-50/60">
            <p className="font-medium text-slate-800">
              {item.name}
              {item.type ? <span className="text-slate-500 font-normal"> ({item.type})</span> : null}
            </p>
            {item.cos.length ? (
              <p className="text-xs text-slate-600 mt-1">
                {item.cos
                  .map((co) => {
                    const attainment =
                      co.attainment != null ? `${co.attainment.toFixed(1)}%` : "N/A";
                    const q = co.question_count != null ? `${co.question_count} q` : "";
                    return `${co.co_label}${q ? ` (${q})` : ""}: ${attainment}`;
                  })
                  .join(" · ")}
              </p>
            ) : (
              <p className="text-xs text-slate-500 mt-1">Structure only — no CO mapping recorded.</p>
            )}
          </li>
        ))}
      </ul>
    );
  }

  return (
    <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
      <h3 className="font-semibold text-slate-800">Assessment structure used for insights</h3>
      <p className="text-xs text-slate-500">
        This data is sent to the LLM when generating insights. Regenerate after new evaluations to refresh.
      </p>
      <div className="grid lg:grid-cols-2 gap-4">
        {comparison.has_previous && (
          <div>
            <h4 className="text-sm font-medium text-slate-700 mb-2">{previousLabel}</h4>
            {hasPrevious ? (
              <>
                <p className="text-xs text-slate-500 mb-2">
                  {formatAssessmentSummary(comparison.previous_assessment_summary)}
                </p>
                {renderAssessments(comparison.previous_assessments)}
              </>
            ) : (
              <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded px-2 py-1.5">
                Backfilled CO/PO only — no assessment structure stored for this semester.
              </p>
            )}
          </div>
        )}
        <div>
          <h4 className="text-sm font-medium text-slate-700 mb-2">{currentLabel}</h4>
          {hasCurrent ? (
            <>
              <p className="text-xs text-slate-500 mb-2">{formatAssessmentSummary(comparison.assessment_summary)}</p>
              {renderAssessments(comparison.current_assessments)}
            </>
          ) : (
            <p className="text-xs text-amber-700 bg-amber-50 border border-amber-100 rounded px-2 py-1.5">
              Backfilled CO/PO only — no assessment structure stored for this semester.
            </p>
          )}
        </div>
      </div>
    </section>
  );
}

export default function LlmInsightsPage() {
  const [courses, setCourses] = useState<InsightCourseOption[]>([]);
  const [selectedKey, setSelectedKey] = useState("");
  const [currentSemester, setCurrentSemester] = useState("");
  const [currentSection, setCurrentSection] = useState("");
  const [previousSemester, setPreviousSemester] = useState("");
  const [previousSection, setPreviousSection] = useState("");
  const [comparison, setComparison] = useState<CourseComparison | null>(null);
  const [insights, setInsights] = useState("");
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [error, setError] = useState("");
  const loadTokenRef = useRef(0);
  const insightsReqRef = useRef(0);
  const comparisonRef = useRef<CourseComparison | null>(null);
  const { provider, setProvider, providers } = useLlmProvider();

  const selectedCourse = useMemo(
    () => courses.find((c) => c.course_key === selectedKey) ?? null,
    [courses, selectedKey]
  );

  const comparisonParams = useMemo(() => {
    if (!selectedCourse) return null;
    return {
      course_title: selectedCourse.course_title,
      current_semester: currentSemester || undefined,
      current_section: currentSection || selectedCourse.section_label || undefined,
      previous_semester: previousSemester || undefined,
      previous_section: previousSection || undefined,
    };
  }, [selectedCourse, currentSemester, currentSection, previousSemester, previousSection]);

  useEffect(() => {
    fetchInsightCourses()
      .then((items) => {
        setCourses(items);
        setError((prev) => (prev.startsWith("Failed to load courses") ? "" : prev));
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load courses"))
      .finally(() => setLoadingCourses(false));
  }, []);

  useEffect(() => {
    if (!selectedCourse) {
      setCurrentSemester("");
      setCurrentSection("");
      setPreviousSemester("");
      setPreviousSection("");
      return;
    }
    const sems = selectedCourse.semesters.length ? selectedCourse.semesters : [selectedCourse.latest_semester];
    setCurrentSemester(sems[sems.length - 1]);
    setCurrentSection(selectedCourse.section_label ?? "");
    if (sems.length >= 2) {
      setPreviousSemester(sems[sems.length - 2]);
      setPreviousSection(selectedCourse.section_label ?? "");
    } else {
      setPreviousSemester("");
      setPreviousSection("");
    }
  }, [selectedKey, selectedCourse]);

  useEffect(() => {
    if (!comparisonParams?.current_semester) {
      comparisonRef.current = null;
      setComparison(null);
      setInsights("");
      setGeneratedAt(null);
      return;
    }

    const token = ++loadTokenRef.current;
    setLoadingComparison(true);

    // Comparison + cached insights load independently. Cache failures are silent.
    // A late failure must not paint a red banner over already-visible comparison
    // (common when Generate is clicked while the initial load is still in flight).
    Promise.allSettled([
      fetchCourseComparison(comparisonParams),
      fetchCachedInsights(comparisonParams),
    ]).then(([compResult, cachedResult]) => {
      if (token !== loadTokenRef.current) return;

      if (compResult.status === "fulfilled") {
        comparisonRef.current = compResult.value;
        setComparison(compResult.value);
        setError("");
      } else if (!comparisonRef.current) {
        const msg =
          compResult.reason instanceof Error
            ? compResult.reason.message
            : "Failed to load course data";
        setError(msg);
      }

      if (cachedResult.status === "fulfilled" && cachedResult.value.insights) {
        setInsights(cachedResult.value.insights);
        setGeneratedAt(cachedResult.value.generated_at);
        if (cachedResult.value.comparison) {
          comparisonRef.current = cachedResult.value.comparison;
          setComparison(cachedResult.value.comparison);
        }
      }
    }).finally(() => {
      if (token === loadTokenRef.current) setLoadingComparison(false);
    });
  }, [comparisonParams]);

  const loadInsights = useCallback(
    async (regenerate = false) => {
      if (!comparisonParams) return;
      const reqId = ++insightsReqRef.current;
      setLoadingInsights(true);
      setError("");
      try {
        const result = await generateLlmInsights({ ...comparisonParams, regenerate, provider });
        if (reqId !== insightsReqRef.current) return;
        if (result.comparison) {
          comparisonRef.current = result.comparison;
          setComparison(result.comparison);
        }
        setInsights(result.insights ?? "");
        setGeneratedAt(result.generated_at);
        setError("");
      } catch (e) {
        if (reqId !== insightsReqRef.current) return;
        setError(e instanceof Error ? e.message : "Could not generate insights at this time. Please try again.");
      } finally {
        if (reqId === insightsReqRef.current) setLoadingInsights(false);
      }
    },
    [comparisonParams, provider]
  );

  const availableSemesters = comparison?.available_semesters ?? selectedCourse?.semesters ?? [];
  const availableSections = comparison?.available_sections ?? [];

  const previousLabel = comparison?.previous_semester
    ? `${comparison.previous_semester}${comparison.previous_section ? ` · Sec ${comparison.previous_section}` : ""}`
    : "Previous";
  const currentLabel = comparison
    ? `${comparison.current_semester}${comparison.current_section ? ` · Sec ${comparison.current_section}` : ""}`
    : "Current";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <span aria-hidden>✨</span> LLM Insights
        </h2>
        <p className="text-sm text-slate-600 mt-1">
          Select a course, semester, and optional section to compare attainment and generate AI recommendations.
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
      )}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-4">
        <div>
          <label className="text-sm font-medium text-slate-700">Select course</label>
          {loadingCourses ? (
            <p className="text-sm text-slate-500 mt-2 animate-pulse">Loading courses…</p>
          ) : !courses.length ? (
            <p className="text-sm text-slate-500 mt-2">No CO-PO evaluation snapshots yet. Run evaluations first.</p>
          ) : (
            <select
              className="mt-2 w-full max-w-xl border rounded-lg px-3 py-2 text-sm"
              value={selectedKey}
              onChange={(e) => setSelectedKey(e.target.value)}
            >
              <option value="">— Choose a course —</option>
              {courses.map((c) => (
                <option key={c.course_key} value={c.course_key}>
                  {c.course_key} — latest: {c.latest_semester}
                </option>
              ))}
            </select>
          )}
        </div>

        {selectedCourse && (
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2 border-t border-slate-100">
            <div>
              <label className="text-xs text-slate-500">Current semester</label>
              <select
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={currentSemester}
                onChange={(e) => setCurrentSemester(e.target.value)}
              >
                {availableSemesters.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Current section (optional)</label>
              <input
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={currentSection}
                onChange={(e) => setCurrentSection(e.target.value.toUpperCase())}
                placeholder={selectedCourse.section_label ? `Default: ${selectedCourse.section_label}` : "None"}
              />
            </div>
            <div>
              <label className="text-xs text-slate-500">Compare with semester</label>
              <select
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={previousSemester}
                onChange={(e) => setPreviousSemester(e.target.value)}
              >
                <option value="">— Auto / none —</option>
                {availableSemesters.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Previous section (optional)</label>
              <input
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={previousSection}
                onChange={(e) => setPreviousSection(e.target.value.toUpperCase())}
                placeholder="Same as current if blank"
                disabled={!previousSemester}
              />
            </div>
          </div>
        )}

        {availableSections.length > 0 && selectedCourse && (
          <p className="text-xs text-slate-500">
            Sections recorded for this course: {availableSections.map((s) => `Section ${s}`).join(", ")}
          </p>
        )}
      </section>

      {selectedCourse && loadingComparison && (
        <p className="text-sm text-slate-500 animate-pulse">Loading attainment comparison…</p>
      )}

      {comparison && selectedCourse && !loadingComparison && (
        <>
          {comparison.insufficient_history && (
            <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              No previous semester selected or available — comparison visuals and delta cards reflect single-semester data
              only.
            </p>
          )}

          <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
            <LlmComparisonVisuals comparison={comparison} />
          </section>

          <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-6">
            <ComparisonTable
              title="CO attainment comparison"
              rows={comparison.co_comparison}
              previousLabel={previousLabel}
              currentLabel={currentLabel}
            />
            <ComparisonTable
              title="PO / PSO attainment comparison"
              rows={comparison.po_comparison}
              previousLabel={previousLabel}
              currentLabel={currentLabel}
            />
          </section>

          <AssessmentStructurePanel
            comparison={comparison}
            previousLabel={previousLabel}
            currentLabel={currentLabel}
          />

          <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
              <h3 className="font-semibold text-slate-800">
                AI Insights — {selectedCourse.course_key} ({currentLabel})
              </h3>
              <div className="flex flex-col items-end gap-2">
                <ProviderSelector
                  provider={provider}
                  onChange={setProvider}
                  providers={providers}
                  disabled={loadingInsights}
                />
                <div className="flex flex-wrap gap-2">
                {!insights && !loadingInsights && (
                  <button
                    type="button"
                    onClick={() => loadInsights(false)}
                    className="text-sm px-3 py-1.5 rounded-lg bg-teal-700 text-white hover:bg-teal-800"
                  >
                    Generate Insights
                  </button>
                )}
                {insights && (
                  <button
                    type="button"
                    disabled={loadingInsights}
                    onClick={() => loadInsights(true)}
                    className="text-sm px-3 py-1.5 rounded-lg border border-slate-300 hover:bg-slate-50 disabled:opacity-50"
                  >
                    Regenerate ↺
                  </button>
                )}
                </div>
              </div>
            </div>

            {!comparison.co_descriptions_available && (
              <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 mb-4">
                CO descriptions not configured. Contact admin to add CO definitions for richer insights.
              </p>
            )}

            {loadingInsights ? (
              <p className="text-sm text-slate-500 animate-pulse py-8 text-center">Generating AI insights…</p>
            ) : insights ? (
              <InsightsBody text={insights} />
            ) : (
              <p className="text-sm text-slate-500 py-6 text-center">
                No insights yet for this selection. Click <strong>Generate Insights</strong> above when you are ready.
              </p>
            )}

            {generatedAt && !loadingInsights && insights && (
              <p className="text-xs text-slate-400 mt-4">Generated on: {new Date(generatedAt).toLocaleString()}</p>
            )}
          </section>
        </>
      )}
    </div>
  );
}
