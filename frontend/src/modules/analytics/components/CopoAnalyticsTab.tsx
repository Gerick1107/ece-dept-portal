import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fetchCopoAnalytics, type CopoAnalyticsData, type CopoRun } from "../services/analyticsApi";
import { CHART_COLORS, ChartCard, KpiCard } from "./ChartCard";

function findRunBySemester(runs: CopoRun[], semester: string): CopoRun | null {
  if (!runs.length) return null;
  return runs.find((r) => r.semester_label === semester) ?? runs[runs.length - 1];
}

function courseSemesters(data: CopoAnalyticsData | null, courseTitle: string): string[] {
  const course = data?.courses.find((c) => c.course_title === courseTitle);
  if (!course) return [];
  return [...new Set(course.runs.map((r) => r.semester_label))];
}

const PO_PSO_KEYS = [
  ...Array.from({ length: 12 }, (_, i) => `PO${i + 1}`),
  "PSO1",
  "PSO2",
  "PSO3",
];

function sortPoPso(keys: string[]): string[] {
  return [...keys].sort((a, b) => {
    const parse = (s: string) => {
      const m = /^(PO|PSO)(\d+)$/i.exec(s.trim());
      if (!m) return [2, 0, s] as const;
      return [m[1].toUpperCase() === "PO" ? 0 : 1, Number(m[2]), ""] as const;
    };
    const [ak, an, as] = parse(a);
    const [bk, bn, bs] = parse(b);
    if (ak !== bk) return ak - bk;
    if (an !== bn) return an - bn;
    return as.localeCompare(bs);
  });
}

function CoTrendTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 shadow-lg rounded-lg px-3 py-2 text-xs">
      <p className="font-medium text-slate-800 mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }}>
          {p.name}: {Number(p.value ?? 0).toFixed(1)}%
        </p>
      ))}
    </div>
  );
}

export default function CopoAnalyticsTab() {
  const [data, setData] = useState<CopoAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [course, setCourse] = useState("");
  const [compareCourseA, setCompareCourseA] = useState("");
  const [compareSemesterA, setCompareSemesterA] = useState("");
  const [compareCourseB, setCompareCourseB] = useState("");
  const [compareSemesterB, setCompareSemesterB] = useState("");
  const [visibleCos, setVisibleCos] = useState<Set<string>>(new Set());
  const [threshold, setThreshold] = useState(60);

  useEffect(() => {
    let cancelled = false;
    fetchCopoAnalytics()
      .then((d) => {
        if (!cancelled) {
          setData(d);
          if (!course && d.course_titles.length) setCourse(d.course_titles[0]);
          if (!compareCourseA && d.course_titles.length) {
            setCompareCourseA(d.course_titles[0]);
            const sems = courseSemesters(d, d.course_titles[0]);
            if (sems.length) setCompareSemesterA(sems[sems.length - 1]);
          }
          if (!compareCourseB && d.course_titles.length) {
            const b = d.course_titles.length > 1 ? d.course_titles[1] : d.course_titles[0];
            setCompareCourseB(b);
            const sems = courseSemesters(d, b);
            if (sems.length) setCompareSemesterB(sems[sems.length - 1]);
          }
        }
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const selected = useMemo(
    () => data?.courses.find((c) => c.course_title === course),
    [data, course]
  );

  const cos = useMemo(() => {
    if (!selected?.runs.length) return [];
    const keys = new Set<string>();
    selected.runs.forEach((run) => {
      (run.unique_cos ?? []).forEach((co) => keys.add(co));
      Object.keys(run.co_attainment ?? {}).forEach((co) => keys.add(co));
    });
    return [...keys].sort((a, b) => {
      const na = Number(a.replace(/\D/g, "")) || 0;
      const nb = Number(b.replace(/\D/g, "")) || 0;
      return na - nb;
    });
  }, [selected]);

  useEffect(() => {
    if (cos.length) setVisibleCos(new Set(cos));
  }, [course, cos.join(",")]);

  const runSeries = useMemo(
    () =>
      (selected?.runs ?? []).map((run: CopoRun, i) => ({
        key: run.run_key || `${run.semester_label} · ${run.public_id.slice(0, 8)}`,
        label: run.semester_label,
        color: CHART_COLORS[i % CHART_COLORS.length],
      })),
    [selected]
  );

  const radarData = useMemo(() => {
    if (!selected) return [];
    return cos.map((co) => {
      const row: Record<string, string | number> = { co };
      selected.runs.forEach((run, i) => {
        row[runSeries[i]?.key ?? run.semester_label] = run.co_attainment[co] ?? 0;
      });
      return row;
    });
  }, [selected, cos, runSeries]);

  const trendData = useMemo(() => {
    if (!selected) return [];
    return selected.runs.map((run, i) => ({
      semester: run.semester_label,
      runKey: runSeries[i]?.key ?? run.semester_label,
      ...run.co_attainment,
    }));
  }, [selected, runSeries]);

  const poChartData = useMemo(() => {
    if (!selected) return [];
    return PO_PSO_KEYS.map((metric) => {
      const row: Record<string, string | number> = { metric };
      selected.runs.forEach((run, i) => {
        row[runSeries[i]?.key ?? run.semester_label] = run.po_attainment[metric] ?? 0;
      });
      return row;
    });
  }, [selected, runSeries]);

  const heatmap = selected?.latest_run?.co_po_mapping ?? {};
  const heatCos = Object.keys(heatmap);
  const heatPos = useMemo(() => {
    const set = new Set<string>();
    heatCos.forEach((co) => Object.keys(heatmap[co] || {}).forEach((po) => set.add(po)));
    return sortPoPso([...set]);
  }, [heatmap, heatCos]);

  const semestersA = useMemo(() => courseSemesters(data, compareCourseA), [data, compareCourseA]);
  const semestersB = useMemo(() => courseSemesters(data, compareCourseB), [data, compareCourseB]);

  useEffect(() => {
    if (semestersA.length && !semestersA.includes(compareSemesterA)) {
      setCompareSemesterA(semestersA[semestersA.length - 1]);
    }
  }, [semestersA, compareSemesterA]);

  useEffect(() => {
    if (semestersB.length && !semestersB.includes(compareSemesterB)) {
      setCompareSemesterB(semestersB[semestersB.length - 1]);
    }
  }, [semestersB, compareSemesterB]);

  const compareARun = useMemo(() => {
    const c = data?.courses.find((x) => x.course_title === compareCourseA);
    return c ? findRunBySemester(c.runs, compareSemesterA) : null;
  }, [data, compareCourseA, compareSemesterA]);

  const compareBRun = useMemo(() => {
    const c = data?.courses.find((x) => x.course_title === compareCourseB);
    return c ? findRunBySemester(c.runs, compareSemesterB) : null;
  }, [data, compareCourseB, compareSemesterB]);

  const compareLabelA = compareARun
    ? `${compareCourseA.split(":")[0]?.trim() || compareCourseA} · ${compareARun.semester_label}`
    : "Series A";
  const compareLabelB = compareBRun
    ? `${compareCourseB.split(":")[0]?.trim() || compareCourseB} · ${compareBRun.semester_label}`
    : "Series B";

  const compareData = useMemo(() => {
    if (!compareARun || !compareBRun) return [];
    const maxLen = Math.max(compareARun.unique_cos.length, compareBRun.unique_cos.length);
    const rows = [];
    for (let i = 0; i < maxLen; i++) {
      const coA = compareARun.unique_cos[i];
      const coB = compareBRun.unique_cos[i];
      rows.push({
        label: `CO${i + 1}`,
        seriesA: coA ? compareARun.co_attainment[coA] ?? 0 : 0,
        seriesB: coB ? compareBRun.co_attainment[coB] ?? 0 : 0,
      });
    }
    return rows;
  }, [compareARun, compareBRun]);

  const barSize = Math.max(6, Math.min(18, Math.floor(60 / Math.max(1, runSeries.length))));

  if (loading) {
    return <p className="text-slate-500 animate-pulse">Loading CO/PO analytics…</p>;
  }
  if (!data || !data.courses.length) {
    return (
      <p className="text-center text-slate-500 py-12">
        No CO/PO analytics snapshots yet. Run evaluations and preserve snapshots via purge or completed runs.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard label="Courses evaluated" value={data.kpis.total_courses} />
        <KpiCard label="Evaluation runs" value={data.kpis.total_runs} />
        <KpiCard label="Avg CO attainment (latest)" value={data.kpis.avg_co_attainment ?? "—"} hint="%" />
        <KpiCard label="Avg PO attainment (latest)" value={data.kpis.avg_po_attainment ?? "—"} hint="%" />
      </div>

      <div className="flex flex-wrap gap-3 bg-white border rounded-xl p-3">
        <select className="border rounded-lg px-3 py-2 text-sm" value={course} onChange={(e) => setCourse(e.target.value)}>
          {data.course_titles.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-sm text-slate-600">
          Target %
          <input
            type="number"
            className="border rounded w-16 px-2 py-1"
            value={threshold}
            onChange={(e) => setThreshold(Number(e.target.value))}
          />
        </label>
      </div>

      {selected && (
        <div className="grid lg:grid-cols-2 gap-4">
          <ChartCard title="CO attainment radar" subtitle={course}>
            <ResponsiveContainer width="100%" height={320}>
              <RadarChart data={radarData}>
                <PolarGrid />
                <PolarAngleAxis dataKey="co" />
                <PolarRadiusAxis domain={[0, 100]} />
                <Tooltip formatter={(v) => `${Number(v ?? 0).toFixed(1)}%`} />
                <Legend />
                {runSeries.map((s) => (
                  <Radar key={s.key} name={s.label} dataKey={s.key} stroke={s.color} fill={s.color} fillOpacity={0.15} />
                ))}
              </RadarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="CO attainment trend" subtitle="Toggle COs below">
            <div className="flex flex-wrap gap-2 mb-2">
              {cos.map((co) => (
                <label key={co} className="text-xs flex items-center gap-1">
                  <input
                    type="checkbox"
                    checked={visibleCos.has(co)}
                    onChange={() => {
                      setVisibleCos((prev) => {
                        const next = new Set(prev);
                        if (next.has(co)) next.delete(co);
                        else next.add(co);
                        return next;
                      });
                    }}
                  />
                  {co}
                </label>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="semester" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 100]} />
                <Tooltip content={<CoTrendTooltip />} />
                <ReferenceLine y={threshold} stroke="#f59e0b" strokeDasharray="4 4" label="Target" />
                <Legend />
                {cos
                  .filter((co) => visibleCos.has(co))
                  .map((co, i) => (
                    <Line
                      key={co}
                      type="monotone"
                      dataKey={co}
                      stroke={CHART_COLORS[i % CHART_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                      connectNulls
                      isAnimationActive={false}
                    />
                  ))}
              </LineChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="PO / PSO attainment by semester" subtitle="PO1–PO12 and PSO1–PSO3">
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={poChartData} barGap={2} barCategoryGap="12%">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="metric" tick={{ fontSize: 9 }} interval={0} angle={-35} textAnchor="end" height={70} />
                <YAxis domain={[0, 100]} />
                <Tooltip formatter={(v) => `${Number(v ?? 0).toFixed(1)}%`} />
                <Legend />
                {runSeries.map((s) => (
                  <Bar
                    key={s.key}
                    dataKey={s.key}
                    name={s.label}
                    fill={s.color}
                    barSize={barSize}
                    isAnimationActive={false}
                  />
                ))}
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          <ChartCard title="CO vs PO heatmap" subtitle="Latest run — mapping weights">
            <div className="overflow-x-auto">
              <table className="text-xs border-collapse min-w-full">
                <thead>
                  <tr>
                    <th className="p-1 border bg-slate-50" />
                    {heatPos.map((po) => (
                      <th key={po} className="p-1 border bg-slate-50 font-medium whitespace-nowrap">
                        {po}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {heatCos.map((co) => (
                    <tr key={co}>
                      <td className="p-1 border font-medium bg-slate-50">{co}</td>
                      {heatPos.map((po) => {
                        const val = heatmap[co]?.[po] ?? 0;
                        const intensity = Math.min(1, val / 3);
                        return (
                          <td
                            key={po}
                            className="p-1 border text-center"
                            style={{
                              backgroundColor: `rgba(15, 118, 110, ${intensity * 0.85})`,
                              color: intensity > 0.5 ? "#fff" : "#334155",
                            }}
                            title={`${co} → ${po}: ${val}`}
                          >
                            {val || "—"}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>
        </div>
      )}

      <ChartCard title="CO attainment comparison" subtitle="Pick course and semester for each series — same or different courses">
        <div className="grid sm:grid-cols-2 gap-4 mb-3">
          <div className="space-y-2 p-3 border rounded-lg bg-slate-50/50">
            <p className="text-xs font-semibold text-slate-600 uppercase">Series A</p>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              value={compareCourseA}
              onChange={(e) => setCompareCourseA(e.target.value)}
            >
              {data.course_titles.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              value={compareSemesterA}
              onChange={(e) => setCompareSemesterA(e.target.value)}
            >
              {semestersA.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2 p-3 border rounded-lg bg-slate-50/50">
            <p className="text-xs font-semibold text-slate-600 uppercase">Series B</p>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              value={compareCourseB}
              onChange={(e) => setCompareCourseB(e.target.value)}
            >
              {data.course_titles.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
              value={compareSemesterB}
              onChange={(e) => setCompareSemesterB(e.target.value)}
            >
              {semestersB.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
        </div>
        <p className="text-xs text-amber-700 mb-2">CO numbering may differ across courses — compare attainment % only.</p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={compareData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis domain={[0, 100]} />
            <Tooltip formatter={(v) => `${Number(v ?? 0).toFixed(1)}%`} />
            <Legend />
            <Bar dataKey="seriesA" fill={CHART_COLORS[0]} name={compareLabelA} />
            <Bar dataKey="seriesB" fill={CHART_COLORS[1]} name={compareLabelB} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
