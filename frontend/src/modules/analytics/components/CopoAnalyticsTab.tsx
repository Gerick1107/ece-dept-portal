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
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { compareSemestersChronological } from "../../course_allocation/utils/semesterUtils";
import { fetchCopoAnalytics, type CopoAnalyticsData, type CopoRun } from "../services/analyticsApi";
import { CHART_COLORS, ChartCard, getColours, divergingCellStyle, KpiCard } from "./ChartCard";

const MAX_COMPARE_SERIES = 6;

type ComparePick = { course: string; semester: string };

function findRunBySemester(runs: CopoRun[], semester: string): CopoRun | null {
  if (!runs.length) return null;
  return (
    runs.find((r) => (r.run_display_label ?? r.semester_label) === semester) ??
    runs.find((r) => r.semester_label === semester) ??
    runs[runs.length - 1]
  );
}

function courseRunLabels(data: CopoAnalyticsData | null, courseKey: string): string[] {
  const course = findCourse(data, courseKey);
  if (!course) return [];
  const labels = course.runs.map((r) => r.run_display_label ?? r.semester_label);
  return [...new Set(labels)].sort(compareSemestersChronological);
}

function findCourse(data: CopoAnalyticsData | null, courseKey: string) {
  if (!data) return null;
  return data.courses.find((c) => c.course_key === courseKey || c.course_title === courseKey) ?? null;
}

function courseSemesters(data: CopoAnalyticsData | null, courseKey: string): string[] {
  const course = findCourse(data, courseKey);
  if (!course) return [];
  return [...new Set(course.runs.map((r) => r.semester_label))].sort(compareSemestersChronological);
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

function defaultComparePicks(data: CopoAnalyticsData, count: number): ComparePick[] {
  const picks: ComparePick[] = [];
  for (let i = 0; i < count; i++) {
    const course = data.course_titles[i] ?? data.course_titles[0] ?? "";
    const sems = courseSemesters(data, course);
    picks.push({ course, semester: sems.length ? sems[sems.length - 1] : "" });
  }
  return picks;
}

export default function CopoAnalyticsTab() {
  const [data, setData] = useState<CopoAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [course, setCourse] = useState("");
  const [seriesCount, setSeriesCount] = useState(2);
  const [comparePicks, setComparePicks] = useState<ComparePick[]>([]);
  const [visibleCos, setVisibleCos] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    fetchCopoAnalytics()
      .then((d) => {
        if (!cancelled) {
          setData(d);
          if (!course && d.course_titles.length) setCourse(d.course_titles[0]);
          setComparePicks(defaultComparePicks(d, 2));
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

  useEffect(() => {
    if (!data) return;
    setComparePicks((prev) => {
      const next = [...prev];
      while (next.length < seriesCount) {
        const idx = next.length;
        const courseKey = data.course_titles[idx] ?? data.course_titles[0] ?? "";
        const sems = courseSemesters(data, courseKey);
        next.push({ course: courseKey, semester: sems.length ? sems[sems.length - 1] : "" });
      }
      return next.slice(0, seriesCount);
    });
  }, [seriesCount, data]);

  const selected = useMemo(() => findCourse(data, course), [data, course]);
  const latestRun = selected?.latest_run ?? selected?.runs[selected.runs.length - 1] ?? null;

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

  const runSeries = useMemo(() => {
    const colors = getColours((selected?.runs ?? []).length);
    return (selected?.runs ?? []).map((run: CopoRun, i) => ({
      key: run.run_key || `${run.semester_label} · ${run.public_id.slice(0, 8)}`,
      label: run.run_display_label ?? run.semester_label,
      color: colors[i] ?? CHART_COLORS[i % CHART_COLORS.length],
    }));
  }, [selected]);

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
      semester: run.run_display_label ?? run.semester_label,
      runKey: runSeries[i]?.key ?? run.semester_label,
      ...run.co_attainment,
    }));
  }, [selected, runSeries]);

  const poChartData = useMemo(() => {
    if (!selected) return [];
    const poKeys = (() => {
      const keys = new Set<string>();
      selected.runs.forEach((run) => {
        Object.keys(run.po_attainment ?? {}).forEach((k) => keys.add(k));
      });
      const ordered = PO_PSO_KEYS.filter((k) => keys.has(k));
      return ordered.length ? ordered : sortPoPso([...keys]);
    })();
    return poKeys.map((metric) => {
      const row: Record<string, string | number> = { metric };
      selected.runs.forEach((run, i) => {
        row[runSeries[i]?.key ?? run.semester_label] = run.po_attainment[metric] ?? 0;
      });
      return row;
    });
  }, [selected, runSeries]);

  const heatmap = latestRun?.co_po_mapping ?? {};
  const heatCos = Object.keys(heatmap);
  const heatPos = useMemo(() => {
    const set = new Set<string>();
    heatCos.forEach((co) => Object.keys(heatmap[co] || {}).forEach((po) => set.add(po)));
    return sortPoPso([...set]);
  }, [heatmap, heatCos]);

  const compareRuns = useMemo(() => {
    return comparePicks.slice(0, seriesCount).map((pick) => {
      const c = findCourse(data, pick.course);
      return c ? { pick, run: findRunBySemester(c.runs, pick.semester) } : { pick, run: null };
    });
  }, [data, comparePicks, seriesCount]);

  useEffect(() => {
    if (!data) return;
    setComparePicks((prev) =>
      prev.map((pick) => {
        const labels = courseRunLabels(data, pick.course);
        if (labels.length && !labels.includes(pick.semester)) {
          return { ...pick, semester: labels[labels.length - 1] };
        }
        return pick;
      })
    );
  }, [data, comparePicks.map((p) => p.course).join("|")]);

  const compareColors = getColours(seriesCount);

  const compareData = useMemo(() => {
    const runs = compareRuns.map((r) => r.run).filter(Boolean) as CopoRun[];
    if (!runs.length) return [];
    const maxLen = Math.max(...runs.map((r) => r.unique_cos.length));
    const rows: Record<string, string | number>[] = [];
    for (let i = 0; i < maxLen; i++) {
      const row: Record<string, string | number> = { label: `CO${i + 1}` };
      compareRuns.forEach((entry, si) => {
        if (!entry.run) {
          row[`series${si}`] = 0;
          return;
        }
        const co = entry.run.unique_cos[i];
        row[`series${si}`] = co ? entry.run.co_attainment[co] ?? 0 : 0;
      });
      rows.push(row);
    }
    return rows;
  }, [compareRuns]);

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
      </div>

      {selected && (
        <div className="grid lg:grid-cols-2 gap-4">
          <ChartCard title="CO attainment radar" subtitle={selected.course_key || course}>
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
                <Legend />
                {(() => {
                  const visible = cos.filter((c) => visibleCos.has(c));
                  const lineColors = getColours(visible.length);
                  return visible.map((co, i) => (
                    <Line
                      key={co}
                      type="monotone"
                      dataKey={co}
                      stroke={lineColors[i] ?? CHART_COLORS[i % CHART_COLORS.length]}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{ r: 6 }}
                      connectNulls
                      isAnimationActive={false}
                    />
                  ));
                })()}
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

          <ChartCard
            title="CO vs PO heatmap"
            subtitle={
              latestRun
                ? `${latestRun.run_display_label ?? latestRun.semester_label} — mapping used at evaluation`
                : "No evaluation run"
            }
          >
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
                        return (
                          <td
                            key={po}
                            className="p-1 border text-center"
                            style={divergingCellStyle(val, 0, 3)}
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
        <div className="flex flex-wrap items-center gap-3 mb-3">
          <label className="text-sm text-slate-600 flex items-center gap-2">
            Series to compare
            <input
              type="number"
              min={2}
              max={MAX_COMPARE_SERIES}
              className="border rounded w-16 px-2 py-1"
              value={seriesCount}
              onChange={(e) => {
                const n = Math.min(MAX_COMPARE_SERIES, Math.max(2, Number(e.target.value) || 2));
                setSeriesCount(n);
              }}
            />
          </label>
          <span className="text-xs text-slate-400">2–{MAX_COMPARE_SERIES} series</span>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-3">
          {comparePicks.slice(0, seriesCount).map((pick, idx) => {
            const semesterOptions = courseRunLabels(data, pick.course);
            return (
              <div key={idx} className="space-y-2 p-3 border rounded-lg bg-slate-50/50">
                <p className="text-xs font-semibold text-slate-600 uppercase">Series {idx + 1}</p>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                  value={pick.course}
                  onChange={(e) => {
                    const courseKey = e.target.value;
                    const sems = courseSemesters(data, courseKey);
                    setComparePicks((prev) => {
                      const next = [...prev];
                      next[idx] = {
                        course: courseKey,
                        semester: sems.length ? sems[sems.length - 1] : "",
                      };
                      return next;
                    });
                  }}
                >
                  {data.course_titles.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <select
                  className="w-full border rounded-lg px-3 py-2 text-sm bg-white"
                  value={pick.semester}
                  onChange={(e) => {
                    const semester = e.target.value;
                    setComparePicks((prev) => {
                      const next = [...prev];
                      next[idx] = { ...next[idx], semester };
                      return next;
                    });
                  }}
                >
                  {semesterOptions.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </div>
            );
          })}
        </div>
        <p className="text-xs text-amber-700 mb-2">CO numbering may differ across courses — compare attainment % only.</p>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={compareData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis domain={[0, 100]} />
            <Tooltip formatter={(v) => `${Number(v ?? 0).toFixed(1)}%`} />
            <Legend />
            {compareRuns.map((entry, i) => {
              if (!entry.run) return null;
              const label = `${entry.pick.course} · ${entry.run.semester_label}`;
              return (
                <Bar
                  key={i}
                  dataKey={`series${i}`}
                  fill={compareColors[i] ?? CHART_COLORS[i % CHART_COLORS.length]}
                  name={label}
                />
              );
            })}
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}
