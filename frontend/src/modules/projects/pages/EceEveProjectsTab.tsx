import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard, getColours, KpiCard } from "../../analytics/components/ChartCard";
import {
  downloadEceEveExport,
  fetchEceEveProjectFilters,
  fetchEceEveProjectsAnalytics,
  listEceEveProjects,
  type EceEveAnalyticsData,
  type EceEveFilterOptions,
  type EceEveProject,
} from "../services/eceEveProjectsApi";

function CommaCell({ value }: { value: string | null | undefined }) {
  const items = (value ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (!items.length) return <>—</>;
  return (
    <div className="flex flex-col gap-0.5 text-xs leading-snug max-w-[12rem]">
      {items.map((item) => (
        <span key={item}>{item}</span>
      ))}
    </div>
  );
}

export default function EceEveProjectsTab() {
  const [items, setItems] = useState<EceEveProject[]>([]);
  const [total, setTotal] = useState(0);
  const [filterOptions, setFilterOptions] = useState<EceEveFilterOptions | null>(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({
    query: "",
    faculty_id: "",
    project_type: "",
    semesters: [] as string[],
    course_codes: [] as string[],
    course_name: "",
    co_guide: "",
    credit: "",
    branch: "both",
    page: 1,
  });

  useEffect(() => {
    fetchEceEveProjectFilters().then(setFilterOptions).catch(() => {});
  }, []);

  const apiFilters = useMemo(
    () => ({
      page: filters.page,
      page_size: 50,
      query: filters.query || undefined,
      faculty_id: filters.faculty_id ? Number(filters.faculty_id) : undefined,
      project_type: filters.project_type || undefined,
      semesters: filters.semesters.length ? filters.semesters.join(",") : undefined,
      course_codes: filters.course_codes.length ? filters.course_codes.join(",") : undefined,
      course_name: filters.course_name || undefined,
      co_guide: filters.co_guide || undefined,
      credit: filters.credit || undefined,
      branch: filters.branch === "both" ? undefined : filters.branch,
    }),
    [filters]
  );

  useEffect(() => {
    setError("");
    listEceEveProjects(apiFilters)
      .then((res) => {
        setItems(res.items);
        setTotal(res.pagination.total);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load projects"));
  }, [apiFilters]);

  function toggleSemesterFilter(tag: string) {
    setFilters((prev) => ({
      ...prev,
      page: 1,
      semesters: prev.semesters.includes(tag) ? prev.semesters.filter((s) => s !== tag) : [...prev.semesters, tag],
    }));
  }

  function toggleCourseCodeFilter(code: string) {
    setFilters((prev) => ({
      ...prev,
      page: 1,
      course_codes: prev.course_codes.includes(code)
        ? prev.course_codes.filter((c) => c !== code)
        : [...prev.course_codes, code],
    }));
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">ECE / EVE Student Projects</h2>
        <p className="text-sm text-slate-600 mt-1">
          Same BTP/IP project view filtered to ECE/EVE student branch, with an added Branch column.
        </p>
      </div>

      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
        <h3 className="text-sm font-semibold text-slate-700">Search & filters</h3>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <input
            placeholder="Search title, guide, students…"
            className="border rounded-lg px-3 py-2 text-sm sm:col-span-2"
            value={filters.query}
            onChange={(e) => setFilters({ ...filters, query: e.target.value, page: 1 })}
          />
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.branch}
            onChange={(e) => setFilters({ ...filters, branch: e.target.value, page: 1 })}
          >
            <option value="both">Branch: Both (ECE + EVE)</option>
            <option value="ECE">Branch: ECE</option>
            <option value="EVE">Branch: EVE</option>
          </select>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.faculty_id}
            onChange={(e) => setFilters({ ...filters, faculty_id: e.target.value, page: 1 })}
          >
            <option value="">Guide (all ECE)</option>
            {filterOptions?.guides.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.project_type}
            onChange={(e) => setFilters({ ...filters, project_type: e.target.value, page: 1 })}
          >
            <option value="">Project type (all)</option>
            {(filterOptions?.project_types ?? ["Thesis", "IP/IS/UR"]).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.course_name}
            onChange={(e) => setFilters({ ...filters, course_name: e.target.value, page: 1 })}
          >
            <option value="">Course name (all)</option>
            {filterOptions?.course_names.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.co_guide}
            onChange={(e) => setFilters({ ...filters, co_guide: e.target.value, page: 1 })}
          >
            <option value="">Co-Guide (all)</option>
            {filterOptions?.co_guides.map((g) => (
              <option key={g} value={g}>
                {g}
              </option>
            ))}
          </select>
          <input
            placeholder="Credit"
            className="border rounded-lg px-3 py-2 text-sm"
            value={filters.credit}
            onChange={(e) => setFilters({ ...filters, credit: e.target.value, page: 1 })}
          />
        </div>
        {filterOptions && filterOptions.semesters.length > 0 && (
          <div>
            <p className="text-xs text-slate-500 mb-1">Semester (multi-select)</p>
            <div className="flex flex-wrap gap-2">
              {filterOptions.semesters.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggleSemesterFilter(tag)}
                  className={`text-xs px-2 py-1 rounded-full border ${
                    filters.semesters.includes(tag)
                      ? "bg-teal-700 text-white border-teal-700"
                      : "bg-white text-slate-700 border-slate-300"
                  }`}
                >
                  {tag}
                </button>
              ))}
            </div>
          </div>
        )}
        {filterOptions && filterOptions.course_codes.length > 0 && (
          <div>
            <p className="text-xs text-slate-500 mb-1">Course code (multi-select)</p>
            <div className="flex flex-wrap gap-2 max-h-24 overflow-y-auto">
              {filterOptions.course_codes.map((code) => (
                <button
                  key={code}
                  type="button"
                  onClick={() => toggleCourseCodeFilter(code)}
                  className={`text-xs px-2 py-1 rounded-full border ${
                    filters.course_codes.includes(code)
                      ? "bg-teal-700 text-white border-teal-700"
                      : "bg-white text-slate-700 border-slate-300"
                  }`}
                >
                  {code}
                </button>
              ))}
            </div>
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => downloadEceEveExport(apiFilters, "xlsx").catch((e) => setError(e instanceof Error ? e.message : "Export failed"))}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
          >
            Export XLSX
          </button>
        </div>
      </section>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto max-h-[70vh] overflow-y-auto">
          <table className="w-full text-sm border-collapse min-w-[1600px]">
            <thead className="sticky top-0 z-10 bg-slate-50 shadow-sm">
              <tr className="text-slate-600 text-left">
                <th className="px-3 py-2 font-medium whitespace-nowrap">Serial Number</th>
                <th className="px-3 py-2 font-medium whitespace-nowrap">Branch</th>
                <th className="px-3 py-2 font-medium min-w-[9rem]">Semester</th>
                <th className="px-3 py-2 font-medium min-w-[14rem]">Title</th>
                <th className="px-3 py-2 font-medium whitespace-nowrap">Course Code</th>
                <th className="px-3 py-2 font-medium min-w-[8rem]">Course Name</th>
                <th className="px-3 py-2 font-medium min-w-[8rem]">Guide</th>
                <th className="px-3 py-2 font-medium min-w-[8rem]">Co-Guide</th>
                <th className="px-3 py-2 font-medium min-w-[9rem]">Student Roll Number</th>
                <th className="px-3 py-2 font-medium min-w-[9rem]">Student Name</th>
                <th className="px-3 py-2 font-medium whitespace-nowrap">Credit</th>
              </tr>
            </thead>
            <tbody>
              {items.map((p, idx) => (
                <tr key={p.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                  <td className="px-3 py-2">{(filters.page - 1) * 50 + idx + 1}</td>
                  <td className="px-3 py-2">{p.program_specialization || "—"}</td>
                  <td className="px-3 py-2"><CommaCell value={p.semesters} /></td>
                  <td className="px-3 py-2 font-medium text-slate-800 max-w-xs">{p.project_title}</td>
                  <td className="px-3 py-2">{p.course_code || "—"}</td>
                  <td className="px-3 py-2">{p.course_name || "—"}</td>
                  <td className="px-3 py-2">{p.guide_name || p.faculty_name || "—"}</td>
                  <td className="px-3 py-2">{p.co_guide || "—"}</td>
                  <td className="px-3 py-2"><CommaCell value={p.student_roll_nos} /></td>
                  <td className="px-3 py-2"><CommaCell value={p.student_names} /></td>
                  <td className="px-3 py-2">{p.credit ?? "—"}</td>
                </tr>
              ))}
              {!items.length && (
                <tr>
                  <td colSpan={11} className="px-3 py-8 text-center text-slate-500">
                    No projects match your filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2 px-3 py-2 border-t text-xs text-slate-500">
          <span>
            Showing {(filters.page - 1) * 50 + 1}–{(filters.page - 1) * 50 + items.length} of {total} projects
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={filters.page <= 1}
              onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
              className="rounded border border-slate-300 px-2 py-1 disabled:opacity-40"
            >
              Previous
            </button>
            <span>Page {filters.page} of {Math.max(1, Math.ceil(total / 50))}</span>
            <button
              type="button"
              disabled={filters.page >= Math.ceil(total / 50)}
              onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
              className="rounded border border-slate-300 px-2 py-1 disabled:opacity-40"
            >
              Next
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export function EceEveProjectsAnalyticsPanel() {
  const [branch, setBranch] = useState<"both" | "ECE" | "EVE">("both");
  const [data, setData] = useState<EceEveAnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    fetchEceEveProjectsAnalytics(branch === "both" ? undefined : branch)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [branch]);

  if (loading) return <p className="text-slate-500 animate-pulse">Loading ECE/EVE project analytics…</p>;
  if (!data) return <p className="text-red-600">Failed to load ECE/EVE project analytics.</p>;
  if (!data.total_count) return <p className="text-center text-slate-500 py-12">No ECE/EVE projects in the database yet.</p>;

  const branchColors = getColours(data.by_branch.length);
  const typeColors = getColours(data.by_type.length);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm font-medium text-slate-700">Branch filter</span>
        {(["both", "ECE", "EVE"] as const).map((value) => (
          <button
            key={value}
            type="button"
            onClick={() => setBranch(value)}
            className={`px-3 py-1.5 text-sm rounded-lg border ${branch === value ? "bg-teal-700 text-white border-teal-700" : "bg-white text-slate-700"}`}
          >
            {value === "both" ? "ECE + EVE" : value}
          </button>
        ))}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard label="Total projects" value={data.total_count} />
        <KpiCard label="Branches" value={data.by_branch.length} />
        <KpiCard label="Project types" value={data.by_type.length} />
        <KpiCard label="Supervisors" value={data.supervisor_distribution.length} />
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <ChartCard title="By branch">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie data={data.by_branch} dataKey="count" nameKey="branch" cx="50%" cy="50%" outerRadius={90} label>
                {data.by_branch.map((_, i) => (
                  <Cell key={i} fill={branchColors[i]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="By project type">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.by_type}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="project_type" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill={typeColors[0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="By semester">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.by_semester}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="semester" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill={getColours(1)[0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Supervisor distribution (top 15)">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={data.supervisor_distribution.slice(0, 15)} layout="vertical" margin={{ left: 80 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" allowDecimals={false} />
              <YAxis type="category" dataKey="supervisor" width={80} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="count" fill={getColours(1)[0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}
