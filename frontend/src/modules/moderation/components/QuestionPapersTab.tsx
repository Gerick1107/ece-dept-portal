import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import {
  createModerationCourse,
  deleteModerationCourse,
  listModerationCourses,
  type ModerationCourse,
} from "../moderationApi";

export default function QuestionPapersTab() {
  const { user } = useAuth();
  const canManage = user?.role === "admin" || user?.role === "faculty" || user?.role === "hod";
  const isAdmin = user?.role === "admin";

  const [courses, setCourses] = useState<ModerationCourse[]>([]);
  const [query, setQuery] = useState("");
  const [facultyQuery, setFacultyQuery] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ course_code: "", course_name: "" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await listModerationCourses({
        query: query || undefined,
        faculty: facultyQuery || undefined,
      });
      setCourses(r.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load courses");
    }
  }, [query, facultyQuery]);

  useEffect(() => {
    load();
  }, [load]);

  async function onAddCourse() {
    if (!form.course_code.trim() || !form.course_name.trim()) {
      setError("Course code and name are required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await createModerationCourse(form);
      setMessage("Course added.");
      setShowAdd(false);
      setForm({ course_code: "", course_name: "" });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not add course");
    } finally {
      setBusy(false);
    }
  }

  const totalPapers = courses.reduce((sum, c) => sum + c.paper_count, 0);
  const distinctFaculty = new Set(courses.flatMap((c) => c.faculty_names)).size;

  return (
    <div className="space-y-4">
      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <div className="grid sm:grid-cols-3 gap-3">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-2xl font-semibold text-teal-800">{courses.length}</p>
          <p className="text-sm text-slate-600 mt-1">Courses</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-2xl font-semibold text-teal-800">{totalPapers}</p>
          <p className="text-sm text-slate-600 mt-1">Question papers</p>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <p className="text-2xl font-semibold text-teal-800">{distinctFaculty}</p>
          <p className="text-sm text-slate-600 mt-1">Faculty represented</p>
        </div>
      </div>

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <input
          placeholder="Search by course code or name…"
          className="border rounded-lg px-3 py-2 text-sm lg:col-span-2"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <input
          placeholder="Search by faculty name…"
          className="border rounded-lg px-3 py-2 text-sm"
          value={facultyQuery}
          onChange={(e) => setFacultyQuery(e.target.value)}
        />
        {canManage && (
          <button
            type="button"
            onClick={() => setShowAdd(true)}
            className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm hover:bg-teal-600"
          >
            Add course
          </button>
        )}
      </section>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm divide-y">
        {courses.map((c) => (
          <Link
            key={c.id}
            to={`/moderation/courses/${c.id}`}
            className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 hover:bg-slate-50/80 transition-colors"
          >
            <div className="min-w-0">
              <p className="font-medium text-slate-900">
                {c.course_code} <span className="font-normal text-slate-600">— {c.course_name}</span>
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                {c.paper_count} paper{c.paper_count === 1 ? "" : "s"}
                {c.faculty_names.length > 0 && ` · ${c.faculty_names.join(", ")}`}
              </p>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-xs text-teal-700 font-medium">View papers →</span>
              {isAdmin && (
                <button
                  type="button"
                  className="text-xs px-2 py-1 rounded bg-red-50 text-red-700"
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    if (!window.confirm(`Delete course "${c.course_code}" and all its papers?`)) return;
                    deleteModerationCourse(c.id).then(() => {
                      setMessage("Course deleted.");
                      load();
                    });
                  }}
                >
                  Delete
                </button>
              )}
            </div>
          </Link>
        ))}
        {!courses.length && (
          <p className="text-center text-slate-500 py-12">No courses match your search.</p>
        )}
      </div>

      {showAdd && canManage && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3">
            <h3 className="font-semibold">Add course</h3>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Course code (e.g. ECE-230)"
              value={form.course_code}
              onChange={(e) => setForm({ ...form, course_code: e.target.value })}
            />
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Course name (e.g. Fields and Waves)"
              value={form.course_name}
              onChange={(e) => setForm({ ...form, course_name: e.target.value })}
            />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowAdd(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50"
                onClick={onAddCourse}
              >
                {busy ? "Adding…" : "Add"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}