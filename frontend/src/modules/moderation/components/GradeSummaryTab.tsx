import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import {
  createGradeCriterion,
  deleteGradeCriterion,
  listGradeCriteria,
  updateGradeCriterion,
  type GradeCriterion,
} from "../moderationApi";

const emptyForm = {
  course_code: "",
  semester: "",
  grade_letter: "",
  min_marks: "",
  max_marks: "",
  remarks: "",
};

export default function GradeSummaryTab() {
  const { user } = useAuth();
  const canManage = user?.role === "admin" || user?.role === "faculty" || user?.role === "hod";
  const isAdmin = user?.role === "admin";

  const [items, setItems] = useState<GradeCriterion[]>([]);
  const [courseFilter, setCourseFilter] = useState("");
  const [semesterFilter, setSemesterFilter] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<GradeCriterion | null>(null);
  const [form, setForm] = useState(emptyForm);

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await listGradeCriteria({
        course_code: courseFilter || undefined,
        semester: semesterFilter || undefined,
      });
      setItems(r.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load grade criteria");
    }
  }, [courseFilter, semesterFilter]);

  useEffect(() => {
    load();
  }, [load]);

  function openAdd() {
    setEditing(null);
    setForm(emptyForm);
    setShowForm(true);
  }

  function openEdit(row: GradeCriterion) {
    setEditing(row);
    setForm({
      course_code: row.course_code,
      semester: row.semester,
      grade_letter: row.grade_letter,
      min_marks: String(row.min_marks),
      max_marks: String(row.max_marks),
      remarks: row.remarks ?? "",
    });
    setShowForm(true);
  }

  async function onSave() {
    const body = {
      course_code: form.course_code.trim(),
      semester: form.semester.trim(),
      grade_letter: form.grade_letter.trim(),
      min_marks: Number(form.min_marks) || 0,
      max_marks: Number(form.max_marks) || 0,
      remarks: form.remarks.trim() || null,
    };
    if (!body.course_code || !body.semester || !body.grade_letter) {
      setError("Course code, semester, and grade letter are required.");
      return;
    }
    setError("");
    try {
      if (editing) {
        await updateGradeCriterion(editing.id, body);
        setMessage("Grade criterion updated.");
      } else {
        await createGradeCriterion(body);
        setMessage("Grade criterion added.");
      }
      setShowForm(false);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    }
  }

  return (
    <div className="space-y-4">
      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          <input
            placeholder="Filter by course code"
            className="border rounded-lg px-3 py-2 text-sm"
            value={courseFilter}
            onChange={(e) => setCourseFilter(e.target.value)}
          />
          <input
            placeholder="Filter by semester"
            className="border rounded-lg px-3 py-2 text-sm"
            value={semesterFilter}
            onChange={(e) => setSemesterFilter(e.target.value)}
          />
        </div>
        {canManage && (
          <button type="button" onClick={openAdd} className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm">
            Add grading criterion
          </button>
        )}
      </div>

      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-slate-50 text-slate-600 text-left">
              <th className="px-4 py-2">Course</th>
              <th className="px-4 py-2">Semester</th>
              <th className="px-4 py-2">Grade</th>
              <th className="px-4 py-2">Marks range</th>
              <th className="px-4 py-2">Remarks</th>
              {canManage && <th className="px-4 py-2" />}
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{row.course_code}</td>
                <td className="px-4 py-2">{row.semester}</td>
                <td className="px-4 py-2 font-medium">{row.grade_letter}</td>
                <td className="px-4 py-2">
                  {row.min_marks} – {row.max_marks}
                </td>
                <td className="px-4 py-2 text-slate-600">{row.remarks || "—"}</td>
                {canManage && (
                  <td className="px-4 py-2 whitespace-nowrap">
                    <button type="button" className="text-xs text-teal-700 mr-3" onClick={() => openEdit(row)}>
                      Edit
                    </button>
                    {isAdmin && (
                      <button
                        type="button"
                        className="text-xs text-red-700"
                        onClick={async () => {
                          if (!window.confirm("Delete this grading criterion?")) return;
                          await deleteGradeCriterion(row.id);
                          setMessage("Grade criterion deleted.");
                          await load();
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                )}
              </tr>
            ))}
            {!items.length && (
              <tr>
                <td colSpan={canManage ? 6 : 5} className="px-4 py-8 text-center text-slate-500">
                  No grading criteria defined yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showForm && canManage && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-3">
            <h3 className="font-semibold">{editing ? "Edit grading criterion" : "Add grading criterion"}</h3>
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Course code (e.g. ECE-230)"
              value={form.course_code}
              onChange={(e) => setForm({ ...form, course_code: e.target.value })}
            />
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Semester (e.g. Monsoon 2026)"
              value={form.semester}
              onChange={(e) => setForm({ ...form, semester: e.target.value })}
            />
            <input
              className="w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="Grade letter (e.g. A+, A, B)"
              value={form.grade_letter}
              onChange={(e) => setForm({ ...form, grade_letter: e.target.value })}
            />
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                className="border rounded-lg px-3 py-2 text-sm"
                placeholder="Min marks"
                value={form.min_marks}
                onChange={(e) => setForm({ ...form, min_marks: e.target.value })}
              />
              <input
                type="number"
                className="border rounded-lg px-3 py-2 text-sm"
                placeholder="Max marks"
                value={form.max_marks}
                onChange={(e) => setForm({ ...form, max_marks: e.target.value })}
              />
            </div>
            <textarea
              className="w-full border rounded-lg px-3 py-2 text-sm min-h-[70px]"
              placeholder="Remarks (optional)"
              value={form.remarks}
              onChange={(e) => setForm({ ...form, remarks: e.target.value })}
            />
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button type="button" className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg" onClick={onSave}>
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}