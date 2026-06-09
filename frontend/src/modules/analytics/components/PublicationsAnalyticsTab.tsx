import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchPublicationsAnalytics, type PublicationsAnalyticsData } from "../services/analyticsApi";
import { CHART_COLORS, ChartCard, KpiCard } from "./ChartCard";

function truncateLabel(value: string, max = 42): string {
  const s = String(value ?? "");
  return s.length > max ? `${s.slice(0, max - 1)}…` : s;
}

export default function PublicationsAnalyticsTab() {
  const [data, setData] = useState<PublicationsAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [venueTab, setVenueTab] = useState<"conference" | "journal" | "publisher">("conference");

  useEffect(() => {
    fetchPublicationsAnalytics().then(setData).catch(() => setData(null)).finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-slate-500 animate-pulse">Loading publications analytics…</p>;

  if (!data || data.is_empty) {
    return (
      <div className="text-center py-16 space-y-3">
        <div className="text-5xl text-slate-300">📚</div>
        <p className="text-slate-600 font-medium">No publications data available yet.</p>
        <p className="text-sm text-slate-500">Publications will appear here once the database is populated.</p>
        <div className="grid sm:grid-cols-3 gap-3 max-w-lg mx-auto mt-6">
          <KpiCard label="Total publications" value={0} />
          <KpiCard label="Total citations" value={0} />
          <KpiCard label="IIITD publications" value={0} />
        </div>
      </div>
    );
  }

  const iiitdPie = [
    { name: "IIITD", value: data.iiitd_split.iiitd },
    { name: "External", value: data.iiitd_split.external },
  ];
  const venues = data.top_venues[venueTab];

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <KpiCard label="Total publications" value={data.kpis.total_publications} />
        <KpiCard label="Patents" value={data.kpis.total_patents} />
        <KpiCard label="Total citations" value={data.kpis.total_citations} />
        <KpiCard label="IIITD publications" value={data.kpis.iiitd_publications} />
        <KpiCard label="Avg citations" value={data.kpis.avg_citations} />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Publications per year">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.year_chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="year" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="journal" stackId="a" fill={CHART_COLORS[0]} />
              <Bar dataKey="conference" stackId="a" fill={CHART_COLORS[2]} />
              <Bar dataKey="book" stackId="a" fill={CHART_COLORS[4]} />
              <Bar dataKey="patent" stackId="a" fill={CHART_COLORS[6]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Publication types">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={data.type_distribution} dataKey="count" nameKey="type" cx="50%" cy="50%" outerRadius={100} label>
                {data.type_distribution.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top venues / journals">
          <div className="flex gap-2 mb-2">
            {(["conference", "journal", "publisher"] as const).map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setVenueTab(t)}
                className={`text-xs px-2 py-1 rounded capitalize ${venueTab === t ? "bg-teal-700 text-white" : "bg-slate-100"}`}
              >
                {t}
              </button>
            ))}
          </div>
          <ResponsiveContainer width="100%" height={Math.max(280, venues.length * 28)}>
            <BarChart data={venues.slice(0, 10)} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis
                type="category"
                dataKey="name"
                width={240}
                tick={{ fontSize: 9 }}
                tickFormatter={(v) => truncateLabel(String(v), 38)}
              />
              <Tooltip
                formatter={(v) => [v, "Publications"]}
                labelFormatter={(label) => String(label)}
              />
              <Bar dataKey="count" fill={CHART_COLORS[1]} barSize={14} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="IIITD vs external">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={iiitdPie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                {iiitdPie.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top cited papers" className="lg:col-span-2">
          <div className="overflow-x-auto max-h-96 overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white">
                <tr className="text-left text-slate-500 border-b">
                  <th className="py-2 pr-2 min-w-[14rem]">Title</th>
                  <th className="py-2 pr-2 min-w-[10rem]">Authors</th>
                  <th className="py-2 pr-2 w-16">Year</th>
                  <th className="py-2 pr-2 min-w-[8rem]">Venue / Journal</th>
                  <th className="py-2 w-20">Citations</th>
                </tr>
              </thead>
              <tbody>
                {data.top_cited.map((row) => (
                  <tr key={`${row.title}-${row.year}`} className="border-b border-slate-100 align-top">
                    <td className="py-2 pr-2" title={row.title}>
                      {row.title}
                    </td>
                    <td className="py-2 pr-2 text-xs text-slate-600 max-w-xs whitespace-normal" title={row.authors ?? ""}>
                      {row.authors || "—"}
                    </td>
                    <td className="py-2 pr-2">{row.year ?? "—"}</td>
                    <td className="py-2 pr-2 text-xs">{truncateLabel(row.venue, 48)}</td>
                    <td className="py-2 font-medium">{row.citations}</td>
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
