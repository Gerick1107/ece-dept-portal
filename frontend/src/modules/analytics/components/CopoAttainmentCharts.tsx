import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchCopoRunAnalytics, type CopoRun } from "../services/analyticsApi";
import { ChartCard, getColours } from "./ChartCard";

const PO_PSO_KEYS = [
  ...Array.from({ length: 12 }, (_, i) => `PO${i + 1}`),
  "PSO1",
  "PSO2",
  "PSO3",
];

type Props = {
  publicId: string;
};

/** CO + PO attainment bar charts for a single evaluation run (Generator dashboard). */
export default function CopoAttainmentCharts({ publicId }: Props) {
  const [run, setRun] = useState<CopoRun | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchCopoRunAnalytics(publicId)
      .then((data) => {
        if (!cancelled) setRun(data?.public_id ? data : null);
      })
      .catch(() => {
        if (!cancelled) setRun(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [publicId]);

  const coChartData = useMemo(() => {
    if (!run) return [];
    const cos = run.unique_cos?.length ? run.unique_cos : Object.keys(run.co_attainment);
    return cos.map((co) => ({ co, attainment: run.co_attainment[co] ?? 0 }));
  }, [run]);

  const poChartData = useMemo(() => {
    if (!run) return [];
    return PO_PSO_KEYS.map((metric) => ({
      metric,
      attainment: run.po_attainment[metric] ?? 0,
    }));
  }, [run]);

  const coColors = useMemo(() => getColours(coChartData.length), [coChartData.length]);
  const poColors = useMemo(() => getColours(poChartData.length), [poChartData.length]);

  if (loading) {
    return <p className="text-sm text-slate-500 animate-pulse">Loading attainment charts…</p>;
  }
  if (!run || (!coChartData.length && !poChartData.some((r) => r.attainment > 0))) {
    return null;
  }

  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <ChartCard title="CO attainment" subtitle={run.semester_label}>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={coChartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="co" />
            <YAxis domain={[0, 100]} />
            <Tooltip formatter={(v) => `${Number(v ?? 0).toFixed(1)}%`} />
            <Legend />
            <Bar dataKey="attainment" name="CO attainment %">
              {coChartData.map((entry, i) => (
                <Cell key={entry.co} fill={coColors[i]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="PO / PSO attainment" subtitle="PO1–PO12 and PSO1–PSO3">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={poChartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="metric" tick={{ fontSize: 9 }} interval={0} angle={-35} textAnchor="end" height={70} />
            <YAxis domain={[0, 100]} />
            <Tooltip formatter={(v) => `${Number(v ?? 0).toFixed(1)}%`} />
            <Legend />
            <Bar dataKey="attainment" name="Attainment %">
              {poChartData.map((entry, i) => (
                <Cell key={entry.metric} fill={poColors[i]} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
