import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ComposedChart, Legend, Line, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchAwardsAnalytics, type AwardsAnalyticsData } from "../services/analyticsApi";
import { ChartCard, divergingCellStyle, getColours, KpiCard } from "./ChartCard";

export default function AwardsAnalyticsTab() {
  const [data, setData] = useState<AwardsAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAwardsAnalytics().then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-slate-500 animate-pulse">Loading awards analytics…</p>;
  if (!data || !data.kpis.total_awards) {
    return <p className="text-center text-slate-500 py-12">No faculty awards data available.</p>;
  }

  const maxHeat = Math.max(1, ...data.heatmap.cells.map((c) => c.count));
  const categoryColors = getColours(data.filter_options.categories.length);
  const facultyBarData = data.faculty_chart.map((f) => ({
    faculty_name: f.faculty_name,
    total: f.total,
    ...f.by_category,
  }));
  const yearLineColors = getColours(2);

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <KpiCard label="Total awards" value={data.kpis.total_awards} />
        <KpiCard label="Faculty with awards" value={data.kpis.faculty_with_awards} />
        <KpiCard
          label="Most awarded faculty"
          value={data.kpis.top_faculty ? `${data.kpis.top_faculty.name} (${data.kpis.top_faculty.count})` : "—"}
        />
        <KpiCard label="Top year" value={data.kpis.top_year ? `${data.kpis.top_year.year} (${data.kpis.top_year.count})` : "—"} />
        <KpiCard label="Top category" value={data.kpis.top_category?.category ?? "—"} />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Awards per faculty" subtitle="Stacked by category">
          <ResponsiveContainer width="100%" height={320}>
            <BarChart data={facultyBarData.slice(0, 20)} layout="vertical" margin={{ left: 100 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="faculty_name" width={95} tick={{ fontSize: 9 }} />
              <Tooltip />
              <Legend />
              {data.filter_options.categories.map((cat, i) => (
                <Bar key={cat} dataKey={cat} stackId="a" fill={categoryColors[i]} name={cat} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Award categories">
          <ResponsiveContainer width="100%" height={320}>
            <PieChart>
              <Pie data={data.category_distribution} dataKey="count" nameKey="category" cx="50%" cy="50%" outerRadius={100} label>
                {data.category_distribution.map((_, i) => (
                  <Cell key={i} fill={categoryColors[i % categoryColors.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Awards over time" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={data.year_chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis yAxisId="left" allowDecimals={false} />
              <YAxis yAxisId="right" orientation="right" allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar yAxisId="left" dataKey="total" fill={yearLineColors[0]} name="Awards per year" />
              <Line yAxisId="right" type="monotone" dataKey="cumulative" stroke={yearLineColors[1]} name="Cumulative" />
            </ComposedChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Faculty × year heatmap" className="lg:col-span-2">
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="text-xs border-collapse">
              <thead>
                <tr>
                  <th className="p-1 border bg-slate-50 sticky left-0">Faculty</th>
                  {data.heatmap.years.map((y) => (
                    <th key={y} className="p-1 border bg-slate-50 whitespace-nowrap">
                      {y}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.heatmap.faculty_names.map((f) => (
                  <tr key={f}>
                    <td className="p-1 border font-medium bg-white sticky left-0">{f}</td>
                    {data.heatmap.years.map((y) => {
                      const cell = data.heatmap.cells.find((c) => c.faculty_name === f && c.year === y);
                      const count = cell?.count ?? 0;
                      return (
                        <td
                          key={y}
                          className="p-1 border text-center min-w-[2rem]"
                          style={divergingCellStyle(count, 0, maxHeat)}
                        >
                          {count || ""}
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
    </div>
  );
}
