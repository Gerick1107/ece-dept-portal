import { useCallback, useEffect, useRef, useState } from "react";
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

export default function LlmInsightsPage() {
  const [courses, setCourses] = useState<InsightCourseOption[]>([]);
  const [selected, setSelected] = useState("");
  const [comparison, setComparison] = useState<CourseComparison | null>(null);
  const [insights, setInsights] = useState("");
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const [loadingCourses, setLoadingCourses] = useState(true);
  const [loadingComparison, setLoadingComparison] = useState(false);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [error, setError] = useState("");
  const loadTokenRef = useRef(0);

  useEffect(() => {
    fetchInsightCourses()
      .then((items) => setCourses(items))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load courses"))
      .finally(() => setLoadingCourses(false));
  }, []);

  useEffect(() => {
    if (!selected) {
      setComparison(null);
      setInsights("");
      setGeneratedAt(null);
      return;
    }

    const token = ++loadTokenRef.current;
    setComparison(null);
    setInsights("");
    setGeneratedAt(null);
    setLoadingComparison(true);
    setError("");

    Promise.all([fetchCourseComparison(selected), fetchCachedInsights(selected)])
      .then(([comp, cached]) => {
        if (token !== loadTokenRef.current) return;
        setComparison(comp);
        if (cached.insights) {
          setInsights(cached.insights);
          setGeneratedAt(cached.generated_at);
        }
      })
      .catch((e) => {
        if (token !== loadTokenRef.current) return;
        setError(e instanceof Error ? e.message : "Failed to load course data");
      })
      .finally(() => {
        if (token === loadTokenRef.current) setLoadingComparison(false);
      });
  }, [selected]);

  const loadInsights = useCallback(
    async (regenerate = false) => {
      if (!selected) return;
      setLoadingInsights(true);
      setError("");
      try {
        const result = await generateLlmInsights({
          course_title: selected,
          regenerate,
        });
        if (result.comparison) setComparison(result.comparison);
        setInsights(result.insights ?? "");
        setGeneratedAt(result.generated_at);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Could not generate insights at this time. Please try again.");
      } finally {
        setLoadingInsights(false);
      }
    },
    [selected]
  );

  const selectedCourse = courses.find((c) => c.course_title === selected);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <span aria-hidden>✨</span> LLM Insights
        </h2>
        <p className="text-sm text-slate-600 mt-1">
          Select a course to view CO/PO comparison tables, then click <strong>Generate Insights</strong> for
          AI recommendations. Insights are generated one course at a time to stay within API limits.
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
      )}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
        <label className="text-sm font-medium text-slate-700">Select course</label>
        {loadingCourses ? (
          <p className="text-sm text-slate-500 mt-2 animate-pulse">Loading courses…</p>
        ) : !courses.length ? (
          <p className="text-sm text-slate-500 mt-2">No CO-PO evaluation snapshots yet. Run evaluations first.</p>
        ) : (
          <select
            className="mt-2 w-full max-w-xl border rounded-lg px-3 py-2 text-sm"
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            <option value="">— Choose a course —</option>
            {courses.map((c) => (
              <option key={c.course_title} value={c.course_title}>
                {c.course_title} — latest: {c.latest_semester}
              </option>
            ))}
          </select>
        )}
      </section>

      {selected && loadingComparison && (
        <p className="text-sm text-slate-500 animate-pulse">Loading attainment comparison…</p>
      )}

      {comparison && selectedCourse && !loadingComparison && (
        <>
          {comparison.insufficient_history && (
            <p className="text-sm text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2">
              No previous semester available for comparison — showing current attainments and general improvement
              strategies.
            </p>
          )}

          <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-6">
            <ComparisonTable
              title="CO attainment comparison"
              rows={comparison.co_comparison}
              previousLabel={comparison.previous_semester ?? "Previous"}
              currentLabel={comparison.current_semester}
            />
            <ComparisonTable
              title="PO / PSO attainment comparison"
              rows={comparison.po_comparison}
              previousLabel={comparison.previous_semester ?? "Previous"}
              currentLabel={comparison.current_semester}
            />
          </section>

          <section className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
            <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
              <h3 className="font-semibold text-slate-800">
                AI Insights — {selectedCourse.course_title} ({comparison.current_semester})
              </h3>
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

            {loadingInsights ? (
              <p className="text-sm text-slate-500 animate-pulse py-8 text-center">Generating AI insights…</p>
            ) : insights ? (
              <InsightsBody text={insights} />
            ) : (
              <p className="text-sm text-slate-500 py-6 text-center">
                No insights yet for this course. Click <strong>Generate Insights</strong> above when you are ready.
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
