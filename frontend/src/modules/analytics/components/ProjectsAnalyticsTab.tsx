import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fetchProjectsAnalytics, type ProjectsAnalyticsData } from "../services/analyticsApi";
import { CHART_COLORS, ChartCard, KpiCard } from "./ChartCard";

export default function ProjectsAnalyticsTab() {
  const [data, setData] = useState<ProjectsAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [projectType, setProjectType] = useState("all");
  const [showAllFaculty, setShowAllFaculty] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchProjectsAnalytics({ project_type: projectType === "all" ? undefined : projectType })
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [projectType]);

  if (loading) return <p className="text-slate-500 animate-pulse">Loading project analytics…</p>;
  if (!data) return <p className="text-red-600">Failed to load project analytics.</p>;
  if (!data.kpis.total_projects) {
    return (
      <p className="text-center text-slate-500 py-12">
        No projects match the selected filter. Try &quot;All project types&quot;.
      </p>
    );
  }

  const facultySlice = showAllFaculty ? data.faculty_load : data.faculty_load.slice(0, 15);
  const typeDonut = [
    { name: "Thesis", value: data.kpis.thesis_count },
    { name: "IP/IS/UR", value: data.kpis.ip_is_ur_count },
  ];

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-5 gap-3">
        <KpiCard label="Total projects" value={data.kpis.total_projects} />
        <KpiCard label="Unique students" value={data.kpis.unique_students} />
        <KpiCard label="Faculty guides" value={data.kpis.unique_guides} />
        <KpiCard label="With co-guide" value={data.kpis.with_co_guide} />
        <KpiCard label="Thesis / IP split" value={`${data.kpis.thesis_count} / ${data.kpis.ip_is_ur_count}`} />
      </div>

      <select className="border rounded-lg px-3 py-2 text-sm bg-white" value={projectType} onChange={(e) => setProjectType(e.target.value)}>
        <option value="all">All project types</option>
        <option value="Thesis">Thesis</option>
        <option value="IP/IS/UR">IP/IS/UR</option>
      </select>

      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="Projects per semester">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data.semester_chart}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="semester" tick={{ fontSize: 10 }} angle={-25} textAnchor="end" height={60} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Bar dataKey="thesis" stackId="a" fill={CHART_COLORS[0]} name="Thesis" />
              <Bar dataKey="ip_is_ur" stackId="a" fill={CHART_COLORS[2]} name="IP/IS/UR" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Thesis vs IP/IS/UR">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie data={typeDonut} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label>
                {typeDonut.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Course code distribution" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={data.course_code_distribution} dataKey="count" nameKey="course_code" cx="50%" cy="50%" outerRadius={110} label>
                {data.course_code_distribution.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Faculty load" subtitle="Guide vs co-guide" className="lg:col-span-2">
          <button type="button" className="text-xs text-teal-700 mb-2" onClick={() => setShowAllFaculty((v) => !v)}>
            {showAllFaculty ? "Show top 15" : "Show all faculty"}
          </button>
          <ResponsiveContainer width="100%" height={Math.max(300, facultySlice.length * 22)}>
            <BarChart data={facultySlice} layout="vertical" margin={{ left: 120 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="faculty_name" width={110} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Legend />
              <Bar dataKey="as_guide" fill={CHART_COLORS[0]} name="As guide" stackId="s" />
              <Bar dataKey="as_co_guide" fill={CHART_COLORS[5]} name="As co-guide" stackId="s" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="SDG review status">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={data.sdg_review_status} dataKey="count" nameKey="status" cx="50%" cy="50%" outerRadius={90} label>
                {data.sdg_review_status.map((_, i) => (
                  <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Top research themes" subtitle="From project titles">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.top_keywords.slice(0, 15)} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="keyword" width={70} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" fill={CHART_COLORS[1]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
