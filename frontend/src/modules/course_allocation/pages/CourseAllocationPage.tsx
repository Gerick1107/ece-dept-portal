import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import {
  downloadAllocationsExport,
  getAllocationDashboardSummary,
  getCurrentSemester,
  listAllocations,
  type AllocationListResponse,
  type DashboardSummary,
} from "../services/courseAllocationApi";
import CourseAllocationAdminPanel from "../components/CourseAllocationAdminPanel";

type FilterKind = "semester" | "academic_year" | "all";

export default function CourseAllocationPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [currentSemester, setCurrentSemester] = useState("Monsoon 2026");
  const [filterKind, setFilterKind] = useState<FilterKind>("semester");
  const [filterValue, setFilterValue] = useState("Monsoon 2026");
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [data, setData] = useState<AllocationListResponse | null>(null);
  const [query, setQuery] = useState("");
  const [ugPg, setUgPg] = useState("");
  const [coreElective, setCoreElective] = useState("");
  const [firstYearOnly, setFirstYearOnly] = useState(false);
  const [filterOptions, setFilterOptions] = useState<{ semesters: string[]; academic_years: string[] }>({
    semesters: [],
    academic_years: [],
  });
  const [error, setError] = useState("");

  const effectiveScope = useMemo(() => {
    if (filterKind === "all") return "all";
    return filterValue;
  }, [filterKind, filterValue]);

  useEffect(() => {
    getCurrentSemester().then((r: { semester: string }) => {
      setCurrentSemester(r.semester);
      setFilterKind("semester");
      setFilterValue(r.semester);
    }).catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setError("");
    try {
      const summarySemester = filterKind === "semester" ? filterValue : currentSemester;
      const [r, dash] = await Promise.all([
        listAllocations({
          scope: effectiveScope,
          query: query || undefined,
          ug_pg: ugPg || undefined,
          core_elective: coreElective || undefined,
          first_year_only: firstYearOnly || undefined,
        }),
        getAllocationDashboardSummary(summarySemester),
      ]);
      setData(r);
      setSummary(dash);
      setFilterOptions({ semesters: r.semesters, academic_years: r.academic_years });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load allocations");
    }
  }, [effectiveScope, query, ugPg, coreElective, firstYearOnly, filterKind, filterValue, currentSemester]);

  useEffect(() => {
    load();
  }, [load]);

  const valueOptions = useMemo(() => {
    if (filterKind === "semester") {
      const semesters = filterOptions.semesters.length ? filterOptions.semesters : [currentSemester];
      return semesters.map((s) => ({ value: s, label: s }));
    }
    if (filterKind === "academic_year") {
      return filterOptions.academic_years.map((ay) => ({ value: ay, label: `Academic year ${ay}` }));
    }
    return [];
  }, [filterKind, filterOptions, currentSemester]);

  useEffect(() => {
    if (filterKind === "all") return;
    if (!valueOptions.length) return;
    if (!valueOptions.some((o) => o.value === filterValue)) {
      setFilterValue(valueOptions[0].value);
    }
  }, [filterKind, valueOptions, filterValue]);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Course Allocations</h2>
          <p className="text-sm text-slate-600 mt-1">Filter by semester, academic year, or view all data.</p>
        </div>
        <button type="button" onClick={() => downloadAllocationsExport(effectiveScope === "all" ? undefined : effectiveScope)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50">
          Export Excel
        </button>
      </div>

      {summary && (
        <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h3 className="font-medium text-slate-800 mb-3">Summary — {summary.semester}</h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-2xl font-semibold text-teal-800">{summary.faculty_teaching}</p>
              <p className="text-xs text-slate-600 mt-1">Faculty teaching</p>
            </div>
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-2xl font-semibold text-teal-800">{summary.total_courses}</p>
              <p className="text-xs text-slate-600 mt-1">Total courses</p>
            </div>
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-2xl font-semibold text-teal-800">{summary.ug_courses} UG · {summary.pg_courses} PG</p>
              <p className="text-xs text-slate-600 mt-1">UG vs PG</p>
            </div>
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-2xl font-semibold text-teal-800">{summary.core_courses} core · {summary.elective_courses} elective</p>
              <p className="text-xs text-slate-600 mt-1">Core vs elective · {summary.first_year_courses} first-year</p>
            </div>
          </div>
        </section>
      )}

      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      {isAdmin && data && data.unmatched.length > 0 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg px-4 py-3 text-sm">
          <strong>{data.unmatched.length}</strong> allocation(s) in this view need faculty name review.
        </div>
      )}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm grid sm:grid-cols-2 lg:grid-cols-6 gap-3">
        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={filterKind}
          onChange={(e) => {
            const kind = e.target.value as FilterKind;
            setFilterKind(kind);
            if (kind === "all") return;
            if (kind === "semester") {
              setFilterValue(filterOptions.semesters[0] ?? currentSemester);
            } else if (filterOptions.academic_years[0]) {
              setFilterValue(filterOptions.academic_years[0]);
            }
          }}
        >
          <option value="semester">By semester</option>
          <option value="academic_year">By academic year</option>
          <option value="all">All data</option>
        </select>
        {filterKind !== "all" && (
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={valueOptions.some((o) => o.value === filterValue) ? filterValue : ""}
            onChange={(e) => setFilterValue(e.target.value)}
            disabled={!valueOptions.length}
          >
            {!valueOptions.length && <option value="">No options</option>}
            {valueOptions.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        )}
        <input placeholder="Search faculty, code, course…" className="border rounded-lg px-3 py-2 text-sm lg:col-span-2" value={query} onChange={(e) => setQuery(e.target.value)} />
        <select className="border rounded-lg px-3 py-2 text-sm" value={ugPg} onChange={(e) => setUgPg(e.target.value)}>
          <option value="">All UG/PG</option>
          <option value="UG">UG</option>
          <option value="PG">PG</option>
          <option value="UG/PG">UG/PG</option>
        </select>
        <select className="border rounded-lg px-3 py-2 text-sm" value={coreElective} onChange={(e) => setCoreElective(e.target.value)}>
          <option value="">All Core/Elective</option>
          <option value="Core">Core</option>
          <option value="Elective">Elective</option>
          <option value="Core/Elective">Core/Elective</option>
        </select>
        <label className="flex items-center gap-2 text-sm lg:col-span-full">
          <input type="checkbox" checked={firstYearOnly} onChange={(e) => setFirstYearOnly(e.target.checked)} />
          First-year courses only
        </label>
      </section>

      <div className="space-y-4">
        {data?.faculty_rows.map((row) => (
          <details key={row.faculty_id} open className="bg-white border border-slate-200 rounded-xl shadow-sm">
            <summary className="cursor-pointer px-4 py-3 font-medium text-slate-800 border-b border-slate-100">
              <Link to={`/course-allocation/faculty/${row.faculty_id}`} className="text-teal-800 hover:underline" onClick={(e) => e.stopPropagation()}>
                {row.faculty_name}
              </Link>
              <span className="text-sm font-normal text-slate-500 ml-2">({row.has_courses ? `${row.courses.length} course(s)` : "NA"})</span>
            </summary>
            {row.has_courses ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[800px]">
                  <thead>
                    <tr className="bg-slate-50 text-slate-600 text-left">
                      <th className="px-4 py-2">Semester</th>
                      <th className="px-4 py-2">Code</th>
                      <th className="px-4 py-2">Course</th>
                      <th className="px-4 py-2">UG/PG</th>
                      <th className="px-4 py-2">Type</th>
                      <th className="px-4 py-2">FY</th>
                    </tr>
                  </thead>
                  <tbody>
                    {row.courses.map((c) => (
                      <tr key={c.id} className="border-t border-slate-100">
                        <td className="px-4 py-2">{c.semester}</td>
                        <td className="px-4 py-2">{c.course_code}</td>
                        <td className="px-4 py-2">{c.course_name}</td>
                        <td className="px-4 py-2">{c.ug_pg}</td>
                        <td className="px-4 py-2">{c.core_elective}</td>
                        <td className="px-4 py-2">{c.is_first_year ? "Yes" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="px-4 py-3 text-sm text-slate-500">NA — no courses in selected scope.</p>
            )}
          </details>
        ))}
      </div>

      {data && data.unassigned.length > 0 && (
        <section className="bg-slate-50 border border-slate-200 rounded-xl p-4">
          <h3 className="font-medium text-slate-800 mb-2">Unassigned / Not offered</h3>
          <ul className="text-sm space-y-1">
            {data.unassigned.map((u) => (
              <li key={u.id}>
                <span className="text-slate-500">{u.semester}</span> — {u.course_code}: {u.course_name}
                {u.faculty_name ? ` (${u.faculty_name})` : ""}
              </li>
            ))}
          </ul>
        </section>
      )}

      {isAdmin && <CourseAllocationAdminPanel scope={effectiveScope} onChanged={load} />}
    </div>
  );
}
