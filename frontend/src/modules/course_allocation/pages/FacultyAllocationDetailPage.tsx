import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getFacultyAllocationHistory, type FacultyAllocationHistory } from "../services/courseAllocationApi";
import { AllocationChartCard, AllocationKpiCard, allocationColours } from "../components/AllocationChartCard";

export default function FacultyAllocationDetailPage() {
  const { facultyId } = useParams<{ facultyId: string }>();
  const [data, setData] = useState<FacultyAllocationHistory | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!facultyId) return;
    getFacultyAllocationHistory(Number(facultyId))
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [facultyId]);

  const ugPgData = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.analytics.ug_pg_split)
      .filter((entry): entry is [string, number] => typeof entry[1] === "number" && entry[1] > 0)
      .map(([name, value]) => ({ name, value }));
  }, [data]);

  const coreElectiveData = useMemo(() => {
    if (!data) return [];
    return Object.entries(data.analytics.core_elective_split)
      .filter((entry): entry is [string, number] => typeof entry[1] === "number" && entry[1] > 0)
      .map(([name, value]) => ({ name, value }));
  }, [data]);

  const pieColours = allocationColours(6);

  if (error) {
    return <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>;
  }
  if (!data) {
    return <p className="text-slate-500 animate-pulse">Loading teaching history…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/course-allocation" className="text-sm text-teal-700 hover:underline">
          ← Course Allocation
        </Link>
        <h2 className="text-xl font-semibold mt-2">{data.faculty.name}</h2>
        <p className="text-sm text-slate-600">Full teaching history across all semesters.</p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <AllocationKpiCard label="Total assignments" value={data.history.length} />
        <AllocationKpiCard label="Distinct courses" value={data.course_counts.length} />
        <AllocationKpiCard label="First-year courses taught" value={data.first_year_counts.reduce((s, r) => s + r.count, 0)} />
        <AllocationKpiCard label="Semesters covered" value={data.analytics.courses_per_semester.length} />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <AllocationChartCard title="Courses per semester">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.analytics.courses_per_semester}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="semester" tick={{ fontSize: 10 }} angle={-25} textAnchor="end" height={60} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#0f766e" name="Courses" />
            </BarChart>
          </ResponsiveContainer>
        </AllocationChartCard>

        <AllocationChartCard title="UG vs PG split">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={ugPgData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                {ugPgData.map((_, i) => (
                  <Cell key={i} fill={pieColours[i]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </AllocationChartCard>

        <AllocationChartCard title="Core vs Elective">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={coreElectiveData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label>
                {coreElectiveData.map((_, i) => (
                  <Cell key={i} fill={pieColours[i]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </AllocationChartCard>

        {data.first_year_counts.length > 0 && (
          <AllocationChartCard title="First-year course frequency">
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={data.first_year_counts} layout="vertical" margin={{ left: 120 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" allowDecimals={false} />
                <YAxis type="category" dataKey="name" width={115} tick={{ fontSize: 9 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#0369a1" name="Times taught" />
              </BarChart>
            </ResponsiveContainer>
          </AllocationChartCard>
        )}
      </div>

      {data.first_year_counts.length > 0 && (
        <section className="bg-teal-50 border border-teal-200 rounded-xl p-4">
          <h3 className="font-medium text-teal-900 mb-2">First-year courses</h3>
          <ul className="text-sm space-y-1">
            {data.first_year_counts.map((r) => (
              <li key={r.name}>
                {r.name} — taught <strong>{r.count}</strong> time{r.count === 1 ? "" : "s"}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        <h3 className="font-medium px-4 py-3 border-b border-slate-100">Times taught per course</h3>
        <table className="w-full text-sm min-w-[700px]">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-left">
              <th className="px-4 py-2">Code</th>
              <th className="px-4 py-2">Course</th>
              <th className="px-4 py-2">Times</th>
              <th className="px-4 py-2">Most recent</th>
              <th className="px-4 py-2">Semesters</th>
            </tr>
          </thead>
          <tbody>
            {data.course_counts.map((c) => (
              <tr key={c.course_code} className="border-t border-slate-100">
                <td className="px-4 py-2">{c.course_code}</td>
                <td className="px-4 py-2">{c.course_name}</td>
                <td className="px-4 py-2">{c.times_taught}</td>
                <td className="px-4 py-2">{c.most_recent_semester}</td>
                <td className="px-4 py-2 text-slate-500">{c.semesters.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        <h3 className="font-medium px-4 py-3 border-b border-slate-100">Full history</h3>
        <table className="w-full text-sm min-w-[800px]">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-left">
              <th className="px-4 py-2">Semester</th>
              <th className="px-4 py-2">AY</th>
              <th className="px-4 py-2">Code</th>
              <th className="px-4 py-2">Course</th>
              <th className="px-4 py-2">UG/PG</th>
              <th className="px-4 py-2">Type</th>
              <th className="px-4 py-2">FY</th>
            </tr>
          </thead>
          <tbody>
            {data.history.map((r) => (
              <tr key={r.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{r.semester}</td>
                <td className="px-4 py-2">{r.academic_year}</td>
                <td className="px-4 py-2">{r.course_code}</td>
                <td className="px-4 py-2">{r.course_name}</td>
                <td className="px-4 py-2">{r.ug_pg}</td>
                <td className="px-4 py-2">{r.core_elective}</td>
                <td className="px-4 py-2">{r.is_first_year ? "Yes" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
