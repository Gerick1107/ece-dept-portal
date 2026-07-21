import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import {
  deletePaper,
  downloadPaper,
  getModerationCourse,
  listCoursePapers,
  uploadCoursePaper,
  type ModerationCourse,
  type QuestionPaper,
} from "../moderationApi";

export default function CourseQuestionPapersPage() {
  const { courseId } = useParams<{ courseId: string }>();
  const id = Number(courseId);
  const { user } = useAuth();
  const canManage = user?.role === "admin" || user?.role === "faculty" || user?.role === "hod";
  const isAdmin = user?.role === "admin";

  const [course, setCourse] = useState<ModerationCourse | null>(null);
  const [papers, setPapers] = useState<QuestionPaper[]>([]);
  const [years, setYears] = useState<number[]>([]);
  const [yearFilter, setYearFilter] = useState("");
  const [sort, setSort] = useState<"asc" | "desc">("desc");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [busy, setBusy] = useState(false);
  const [pdfBusyId, setPdfBusyId] = useState<number | null>(null);
  const [form, setForm] = useState({
    faculty_name: "",
    year: String(new Date().getFullYear()),
    semester: "Monsoon" as "Winter" | "Monsoon",
    file: null as File | null,
  });

  const load = useCallback(async () => {
    if (!id) return;
    setError("");
    try {
      const [c, p] = await Promise.all([
        getModerationCourse(id),
        listCoursePapers(id, { year: yearFilter ? Number(yearFilter) : undefined, sort }),
      ]);
      setCourse(c);
      setPapers(p.items);
      setYears(p.years);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load course");
    }
  }, [id, yearFilter, sort]);

  useEffect(() => {
    load();
  }, [load]);

  async function onUpload() {
    if (!form.faculty_name.trim() || !form.year || !form.file) {
      setError("Faculty name, year, and a PDF file are required.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await uploadCoursePaper(id, {
        faculty_name: form.faculty_name.trim(),
        year: Number(form.year),
        semester: form.semester,
        file: form.file,
      });
      setMessage("Question paper uploaded.");
      setShowUpload(false);
      setForm({ faculty_name: "", year: String(new Date().getFullYear()), semester: "Monsoon", file: null });
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  if (!course) {
    return error ? (
      <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
    ) : (
      <p className="text-slate-500 animate-pulse">Loading course…</p>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <Link to="/moderation" className="text-sm text-teal-700 hover:underline">
          ← Moderation
        </Link>
        <h2 className="text-xl font-semibold mt-2">
          {course.course_code}: {course.course_name}
        </h2>
        <p className="text-sm text-slate-600 mt-1">Question papers uploaded for this course.</p>
      </div>

      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="border rounded-lg px-3 py-2 text-sm"
            value={yearFilter}
            onChange={(e) => setYearFilter(e.target.value)}
          >
            <option value="">All years</option>
            {years.map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="text-sm border border-slate-300 rounded-lg px-3 py-2 hover:bg-slate-50"
            onClick={() => setSort((s) => (s === "desc" ? "asc" : "desc"))}
          >
            Sort by year: {sort === "desc" ? "Newest first ↓" : "Oldest first ↑"}
          </button>
        </div>
        {canManage && (
          <button
            type="button"
            onClick={() => setShowUpload(true)}
            className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm hover:bg-teal-600"
          >
            Upload question paper
          </button>
        )}
      </section>

      <div className="bg-white border border-slate-200 rounded-xl shadow-sm overflow-x-auto">
        <table className="w-full text-sm min-w-[700px]">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-left">
              <th className="px-4 py-2 font-medium">Faculty</th>
              <th className="px-4 py-2 font-medium">Year</th>
              <th className="px-4 py-2 font-medium">Semester</th>
              <th className="px-4 py-2 font-medium">File</th>
              <th className="px-4 py-2 font-medium">Uploaded</th>
              <th className="px-4 py-2 font-medium w-40">Actions</th>
            </tr>
          </thead>
          <tbody>
            {papers.map((p) => (
              <tr key={p.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{p.faculty_name}</td>
                <td className="px-4 py-2">{p.year}</td>
                <td className="px-4 py-2">{p.semester}</td>
                <td className="px-4 py-2 text-slate-600">{p.original_filename}</td>
                <td className="px-4 py-2 text-xs text-slate-500">
                  {p.uploaded_at ? new Date(p.uploaded_at).toLocaleString() : "—"}
                </td>
                <td className="px-4 py-2 whitespace-nowrap">
                  <button
                    type="button"
                    className="text-xs px-2 py-1 rounded bg-slate-100 mr-2 disabled:opacity-50"
                    disabled={pdfBusyId === p.id}
                    onClick={async () => {
                      setPdfBusyId(p.id);
                      try {
                        await downloadPaper(p.id, p.original_filename);
                      } catch {
                        setError("Download failed");
                      } finally {
                        setPdfBusyId(null);
                      }
                    }}
                  >
                    {pdfBusyId === p.id ? "Opening…" : "View / Download"}
                  </button>
                  {isAdmin && (
                    <button
                      type="button"
                      className="text-xs px-2 py-1 rounded bg-red-50 text-red-700"
                      onClick={async () => {
                        if (!window.confirm("Delete this question paper?")) return;
                        await deletePaper(p.id);
                        setMessage("Question paper deleted.");
                        await load();
                      }}
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!papers.length && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-slate-500">
                  No question papers uploaded for this course yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showUpload && canManage && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3">
            <h3 className="font-semibold">Upload question paper</h3>
            <p className="text-xs text-slate-500">
              {course.course_code}: {course.course_name}
            </p>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Faculty name"
              value={form.faculty_name}
              onChange={(e) => setForm({ ...form, faculty_name: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                className="border rounded-lg px-3 py-2 text-sm"
                placeholder="Year"
                value={form.year}
                onChange={(e) => setForm({ ...form, year: e.target.value })}
              />
              <select
                className="border rounded-lg px-3 py-2 text-sm"
                value={form.semester}
                onChange={(e) => setForm({ ...form, semester: e.target.value as "Winter" | "Monsoon" })}
              >
                <option value="Monsoon">Monsoon</option>
                <option value="Winter">Winter</option>
              </select>
            </div>
            <input
              type="file"
              accept="application/pdf"
              className="text-sm"
              onChange={(e) => setForm({ ...form, file: e.target.files?.[0] ?? null })}
            />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowUpload(false)}>
                Cancel
              </button>
              <button
                type="button"
                disabled={busy}
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50"
                onClick={onUpload}
              >
                {busy ? "Uploading…" : "Upload"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}