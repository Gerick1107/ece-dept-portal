import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  downloadCoursesAllocationsExport,
  getCoursesDashboardSummary,
  getCurrentSemester,
  listCoursesAllocations,
  type CourseListResponse,
  type CoursesDashboardSummary,
} from "../services/courseAllocationApi";

type FilterKind = "semester" | "academic_year" | "all";

export default function CourseWiseAllocationPage() {
  const [currentSemester, setCurrentSemester] = useState("Monsoon 2026");
  const [filterKind, setFilterKind] = useState<FilterKind>("semester");
  const [filterValue, setFilterValue] = useState("Monsoon 2026");
  const [summary, setSummary] = useState<CoursesDashboardSummary | null>(null);
  const [data, setData] = useState<CourseListResponse | null>(null);
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
    getCurrentSemester()
      .then((r: { semester: string }) => {
        setCurrentSemester(r.semester);
        setFilterKind("semester");
        setFilterValue(r.semester);
      })
      .catch(() => {});
  }, []);

  const load = useCallback(async () => {
    setError("");
    try {
      const summarySemester = filterKind === "semester" ? filterValue : currentSemester;
      const [r, dash] = await Promise.all([
        listCoursesAllocations({
          scope: effectiveScope,
          query: query || undefined,
          ug_pg: ugPg || undefined,
          core_elective: coreElective || undefined,
          first_year_only: firstYearOnly || undefined,
        }),
        getCoursesDashboardSummary(summarySemester),
      ]);
      setData(r);
      setSummary(dash);
      setFilterOptions({ semesters: r.semesters, academic_years: r.academic_years });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load course allocations");
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
          <h2 className="text-xl font-semibold">Course-Wise Allocations</h2>
          <p className="text-sm text-slate-600 mt-1">Filter by semester, academic year, or view all data — grouped by canonical course.</p>
        </div>
        <button
          type="button"
          onClick={() => downloadCoursesAllocationsExport(effectiveScope === "all" ? undefined : effectiveScope)}
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
        >
          Export Excel
        </button>
      </div>

      {summary && (
        <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
          <h3 className="font-medium text-slate-800 mb-3">Summary — {summary.semester}</h3>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-2xl font-semibold text-teal-800">{summary.total_courses}</p>
              <p className="text-xs text-slate-600 mt-1">Distinct courses</p>
            </div>
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-2xl font-semibold text-teal-800">{summary.faculty_involved}</p>
              <p className="text-xs text-slate-600 mt-1">Faculty involved</p>
            </div>
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-2xl font-semibold text-teal-800">
                {summary.ug_courses} UG · {summary.pg_courses} PG
              </p>
              <p className="text-xs text-slate-600 mt-1">UG vs PG (instances)</p>
            </div>
            <div className="rounded-lg bg-slate-50 border border-slate-100 p-3">
              <p className="text-2xl font-semibold text-teal-800">
                {summary.core_courses} core · {summary.elective_courses} elective
              </p>
              <p className="text-xs text-slate-600 mt-1">
                Core vs elective · {summary.first_year_courses} first-year
              </p>
            </div>
          </div>
        </section>
      )}

      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

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
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        )}
        <input
          placeholder="Search course, code, faculty…"
          className="border rounded-lg px-3 py-2 text-sm lg:col-span-2"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <select className="border rounded-lg px-3 py-2 text-sm" value={ugPg} onChange={(e) => setUgPg(e.target.value)}>
          <option value="">All UG/PG</option>
          <option value="UG">UG</option>
          <option value="PG">PG</option>
          <option value="UG/PG">UG/PG</option>
        </select>
        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={coreElective}
          onChange={(e) => setCoreElective(e.target.value)}
        >
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
        {data?.course_rows.map((row) => (
          <details key={row.course_key} open className="bg-white border border-slate-200 rounded-xl shadow-sm">
            <summary className="cursor-pointer px-4 py-3 font-medium text-slate-800 border-b border-slate-100">
              {row.course_catalog_id ? (
                <Link
                  to={`/course-allocation/course/${row.course_catalog_id}`}
                  className="text-teal-800 hover:underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  {row.course_code}: {row.course_name}
                </Link>
              ) : (
                <span>
                  {row.course_code}: {row.course_name}
                </span>
              )}
              <span className="text-sm font-normal text-slate-500 ml-2">
                ({row.has_allocations ? `${row.allocations.length} instance(s)` : "NA"})
              </span>
            </summary>
            {row.has_allocations ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm min-w-[900px]">
                  <thead>
                    <tr className="bg-slate-50 text-slate-600 text-left">
                      <th className="px-4 py-2">Semester</th>
                      <th className="px-4 py-2">Code</th>
                      <th className="px-4 py-2">Course</th>
                      <th className="px-4 py-2">Faculty</th>
                      <th className="px-4 py-2">UG/PG</th>
                      <th className="px-4 py-2">Type</th>
                      <th className="px-4 py-2">FY</th>
                    </tr>
                  </thead>
                  <tbody>
                    {row.allocations.map((a) => (
                      <tr key={a.id} className="border-t border-slate-100">
                        <td className="px-4 py-2">{a.semester}</td>
                        <td className="px-4 py-2">{a.course_code}</td>
                        <td className="px-4 py-2">{a.course_name}</td>
                        <td className="px-4 py-2">{a.faculty_name}</td>
                        <td className="px-4 py-2">{a.ug_pg}</td>
                        <td className="px-4 py-2">{a.core_elective}</td>
                        <td className="px-4 py-2">{a.is_first_year ? "Yes" : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="px-4 py-3 text-sm text-slate-500">NA — no allocations in selected scope.</p>
            )}
          </details>
        ))}
      </div>
    </div>
  );
}
