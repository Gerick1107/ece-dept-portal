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
import { getCourseAllocationHistory, type CourseAllocationHistory } from "../services/courseAllocationApi";
import { AllocationChartCard, AllocationKpiCard, allocationColours } from "../components/AllocationChartCard";

export default function CourseAllocationDetailPage() {
  const { courseCatalogId } = useParams<{ courseCatalogId: string }>();
  const [data, setData] = useState<CourseAllocationHistory | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!courseCatalogId) return;
    getCourseAllocationHistory(Number(courseCatalogId))
      .then(setData)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load"));
  }, [courseCatalogId]);

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
    return <p className="text-slate-500 animate-pulse">Loading course history…</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/course-allocation/courses" className="text-sm text-teal-700 hover:underline">
          ← Course-Wise Allocations
        </Link>
        <h2 className="text-xl font-semibold mt-2">
          {data.course.course_code}: {data.course.course_name}
        </h2>
        <p className="text-sm text-slate-600">Full offering history across all semesters.</p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <AllocationKpiCard label="Total instances" value={data.history.length} />
        <AllocationKpiCard label="Distinct faculty" value={data.faculty_counts.length} />
        <AllocationKpiCard
          label="Semesters offered"
          value={data.analytics.instances_per_semester.length}
        />
        <AllocationKpiCard
          label="Most recent semester"
          value={
            data.analytics.instances_per_semester.length
              ? data.analytics.instances_per_semester[data.analytics.instances_per_semester.length - 1].semester
              : "—"
          }
        />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <AllocationChartCard title="Instances per semester">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.analytics.instances_per_semester}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="semester" tick={{ fontSize: 10 }} angle={-25} textAnchor="end" height={60} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#0f766e" name="Instances" />
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
      </div>

      <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        <h3 className="font-medium px-4 py-3 border-b border-slate-100">Faculty who taught this course</h3>
        <table className="w-full text-sm min-w-[700px]">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-left">
              <th className="px-4 py-2">Faculty</th>
              <th className="px-4 py-2">Times</th>
              <th className="px-4 py-2">Most recent</th>
              <th className="px-4 py-2">Semesters</th>
            </tr>
          </thead>
          <tbody>
            {data.faculty_counts.map((f) => (
              <tr key={f.faculty_id ?? f.faculty_name} className="border-t border-slate-100">
                <td className="px-4 py-2">
                  {f.faculty_id ? (
                    <Link to={`/course-allocation/faculty/${f.faculty_id}`} className="text-teal-800 hover:underline">
                      {f.faculty_name}
                    </Link>
                  ) : (
                    f.faculty_name
                  )}
                </td>
                <td className="px-4 py-2">{f.times_taught}</td>
                <td className="px-4 py-2">{f.most_recent_semester}</td>
                <td className="px-4 py-2 text-slate-500">{f.semesters.join(", ")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        <h3 className="font-medium px-4 py-3 border-b border-slate-100">Full history</h3>
        <table className="w-full text-sm min-w-[900px]">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-left">
              <th className="px-4 py-2">Semester</th>
              <th className="px-4 py-2">AY</th>
              <th className="px-4 py-2">Faculty</th>
              <th className="px-4 py-2">Code</th>
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
                <td className="px-4 py-2">{r.faculty_name}</td>
                <td className="px-4 py-2">{r.course_code}</td>
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
