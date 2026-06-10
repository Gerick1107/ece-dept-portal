import { useMemo } from "react";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard, KpiCard } from "../../analytics/components/ChartCard";
import type { ComparisonRow, CourseComparison } from "../services/llmInsightsApi";

const PREV_COLOR = "#94a3b8";
const CURR_COLOR = "#1a6fba";

function summarizeRows(rows: ComparisonRow[], hasPrevious: boolean) {
  const declined = rows.filter((r) => r.trend === "down").length;
  const improved = rows.filter((r) => r.trend === "up").length;
  const currVals = rows.map((r) => r.current).filter((v): v is number => v != null);
  const prevVals = rows.map((r) => r.previous).filter((v): v is number => v != null);
  const avgCurrent = currVals.length ? currVals.reduce((a, b) => a + b, 0) / currVals.length : null;
  const avgPrevious = prevVals.length ? prevVals.reduce((a, b) => a + b, 0) / prevVals.length : null;
  const delta =
    hasPrevious && avgCurrent != null && avgPrevious != null ? avgCurrent - avgPrevious : null;
  return { declined, improved, avgCurrent, avgPrevious, delta };
}

function SummaryCards({
  title,
  rows,
  hasPrevious,
}: {
  title: string;
  rows: ComparisonRow[];
  hasPrevious: boolean;
}) {
  const stats = summarizeRows(rows, hasPrevious);
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold text-slate-700">{title}</h4>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
        {hasPrevious && (
          <>
            <div className="rounded-xl border border-red-200 bg-red-50/80 p-3 shadow-sm">
              <p className="text-2xl font-semibold text-red-700">▼ {stats.declined}</p>
              <p className="text-xs text-red-800/80 mt-1">Declined</p>
            </div>
            <div className="rounded-xl border border-emerald-200 bg-emerald-50/80 p-3 shadow-sm">
              <p className="text-2xl font-semibold text-emerald-700">▲ {stats.improved}</p>
              <p className="text-xs text-emerald-800/80 mt-1">Improved</p>
            </div>
          </>
        )}
        <div className="rounded-xl border border-sky-200 bg-sky-50/80 p-3 shadow-sm">
          <p className="text-2xl font-semibold text-sky-800">
            {stats.avgCurrent != null ? `${stats.avgCurrent.toFixed(1)}%` : "—"}
          </p>
          <p className="text-xs text-sky-900/80 mt-1">Avg current</p>
        </div>
        {hasPrevious && (
          <>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-3 shadow-sm">
              <p className="text-2xl font-semibold text-slate-700">
                {stats.avgPrevious != null ? `${stats.avgPrevious.toFixed(1)}%` : "—"}
              </p>
              <p className="text-xs text-slate-600 mt-1">Avg previous</p>
            </div>
            <div
              className={`rounded-xl border p-3 shadow-sm ${
                stats.delta != null && stats.delta < 0
                  ? "border-red-200 bg-red-50/60"
                  : stats.delta != null && stats.delta > 0
                    ? "border-emerald-200 bg-emerald-50/60"
                    : "border-slate-200 bg-slate-50"
              }`}
            >
              <p className="text-2xl font-semibold text-slate-800">
                {stats.delta != null
                  ? `${stats.delta > 0 ? "▲" : stats.delta < 0 ? "▼" : "•"} ${stats.delta > 0 ? "+" : ""}${stats.delta.toFixed(1)}%`
                  : "—"}
              </p>
              <p className="text-xs text-slate-600 mt-1">Overall Δ</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function GroupedBarChart({
  title,
  rows,
  previousLabel,
  currentLabel,
}: {
  title: string;
  rows: ComparisonRow[];
  previousLabel: string;
  currentLabel: string;
}) {
  const data = useMemo(
    () =>
      rows
        .filter((r) => r.current != null || r.previous != null)
        .map((r) => ({
          metric: r.metric,
          previous: r.previous ?? 0,
          current: r.current ?? 0,
        })),
    [rows]
  );

  if (!data.length) return null;

  return (
    <ChartCard title={title}>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data} barGap={2} barCategoryGap="18%">
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="metric" tick={{ fontSize: 11 }} />
          <YAxis domain={[0, 100]} />
          <Tooltip formatter={(v) => `${Number(v ?? 0).toFixed(1)}%`} />
          <Legend />
          <Bar dataKey="previous" name={previousLabel} fill={PREV_COLOR} />
          <Bar dataKey="current" name={currentLabel} fill={CURR_COLOR} />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  );
}

type Props = {
  comparison: CourseComparison;
};

export default function LlmComparisonVisuals({ comparison }: Props) {
  const hasPrevious = comparison.has_previous && !comparison.insufficient_history;
  const prevLabel = comparison.previous_semester ?? "Previous";
  const currLabel = comparison.current_semester;

  return (
    <div className="space-y-6">
      <SummaryCards title="CO summary" rows={comparison.co_comparison} hasPrevious={hasPrevious} />
      {hasPrevious && (
        <GroupedBarChart
          title={`CO Attainment: ${prevLabel} vs ${currLabel}`}
          rows={comparison.co_comparison}
          previousLabel={prevLabel}
          currentLabel={currLabel}
        />
      )}

      <SummaryCards title="PO / PSO summary" rows={comparison.po_comparison} hasPrevious={hasPrevious} />
      {hasPrevious && (
        <GroupedBarChart
          title={`PO / PSO Attainment: ${prevLabel} vs ${currLabel}`}
          rows={comparison.po_comparison}
          previousLabel={prevLabel}
          currentLabel={currLabel}
        />
      )}

      {comparison.assessment_summary.length > 0 ? (
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-slate-700">Assessment Structure (Current Semester)</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
            {comparison.assessment_summary.map((item) => (
              <KpiCard
                key={item.component_type}
                label={item.component_type}
                value={item.component_count}
                hint={`${item.total_questions} question column(s)`}
              />
            ))}
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500 italic">No assessment data available for this course.</p>
      )}
    </div>
  );
}
