import { useEffect, useState } from "react";
import { listFaculty } from "../../publications/services/publicationsApi";
import type { Faculty } from "../../publications/types/publications";
import {
  createAllocation,
  listCourseCatalog,
  updateAllocation,
  type AllocationCourse,
  type CatalogEntry,
} from "../services/courseAllocationApi";
import { academicYearForSemester } from "../utils/semesterUtils";

type Props = {
  initial?: AllocationCourse | null;
  defaults?: Partial<AllocationCourse>;
  onClose: () => void;
  onSaved: (message: string) => void;
  onError: (message: string) => void;
};

const TYPE_OPTIONS = ["", "Core", "Elective", "Core/Elective"] as const;

type FormState = {
  faculty_id: string;
  faculty_name: string;
  unassigned: boolean;
  semester: string;
  academic_year: string;
  course_catalog_id: string;
  course_code: string;
  course_name: string;
  ug_type: string;
  pg_type: string;
  registered_students: string;
};

function toForm(initial?: AllocationCourse | null, defaults?: Partial<AllocationCourse>): FormState {
  const base = { ...(defaults ?? {}), ...(initial ?? {}) };
  const hasFaculty = base.faculty_id != null || Boolean(base.faculty_name?.trim());
  return {
    faculty_id: base.faculty_id != null ? String(base.faculty_id) : "",
    faculty_name: base.faculty_name ?? "",
    unassigned: Boolean(base.is_faculty_placeholder) || (Boolean(initial) && !hasFaculty),
    semester: base.semester ?? "",
    academic_year: base.academic_year ?? "",
    course_catalog_id: base.course_catalog_id != null ? String(base.course_catalog_id) : "",
    course_code: base.course_code ?? "",
    course_name: base.course_name ?? "",
    ug_type: base.ug_type ?? "",
    pg_type: base.pg_type ?? "",
    registered_students: base.registered_students != null ? String(base.registered_students) : "",
  };
}

export default function AllocationFormModal({ initial, defaults, onClose, onSaved, onError }: Props) {
  const editing = Boolean(initial?.id);
  const [form, setForm] = useState<FormState>(() => toForm(initial, defaults));
  const [eceFaculty, setEceFaculty] = useState<Faculty[]>([]);
  const [catalog, setCatalog] = useState<CatalogEntry[]>([]);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listFaculty({ page: 1, page_size: 200, include_inactive: false })
      .then((r) => setEceFaculty(r.items.filter((f) => f.department?.includes("ECE"))))
      .catch(() => {});
    listCourseCatalog()
      .then((r) => setCatalog(r.items ?? []))
      .catch(() => {});
  }, []);

  function applyCatalog(entryId: string) {
    const entry = catalog.find((c) => String(c.id) === entryId);
    if (!entry) {
      setForm((prev) => ({ ...prev, course_catalog_id: entryId }));
      return;
    }
    setForm((prev) => ({
      ...prev,
      course_catalog_id: String(entry.id),
      course_code: entry.course_code,
      course_name: entry.course_name,
      ug_type: entry.ug_type ?? "",
      pg_type: entry.pg_type ?? "",
    }));
  }

  async function save() {
    if (!form.semester.trim() || !form.course_code.trim() || !form.course_name.trim()) {
      onError("Semester, course code, and course name are required.");
      return;
    }
    if (!form.unassigned && !form.faculty_id) {
      onError("Select a faculty member, or mark the allocation as unassigned.");
      return;
    }

    const selected = eceFaculty.find((f) => String(f.id) === form.faculty_id);
    const academicYear =
      form.academic_year.trim() || academicYearForSemester(form.semester.trim()) || form.academic_year;
    const regRaw = form.registered_students.trim();
    const registeredStudents = regRaw === "" ? null : Number(regRaw);
    if (regRaw !== "" && (!Number.isFinite(registeredStudents) || (registeredStudents ?? 0) < 0)) {
      onError("Registered students must be a non-negative number.");
      return;
    }

    const payload = {
      semester: form.semester.trim(),
      academic_year: academicYear,
      course_code: form.course_code.trim(),
      course_name: form.course_name.trim(),
      ug_type: form.ug_type || null,
      pg_type: form.pg_type || null,
      registered_students: registeredStudents,
      clear_registered_students: regRaw === "",
      course_catalog_id: form.course_catalog_id ? Number(form.course_catalog_id) : null,
      faculty_id: form.unassigned ? null : Number(form.faculty_id),
      faculty_name: form.unassigned
        ? form.faculty_name.trim() || "Not Assigned"
        : selected?.name || form.faculty_name.trim(),
      is_faculty_placeholder: form.unassigned,
      clear_faculty: form.unassigned,
      source: editing ? undefined : "manual",
    };

    setBusy(true);
    try {
      if (editing && initial) {
        await updateAllocation(initial.id, payload);
        onSaved("Allocation updated.");
      } else {
        await createAllocation(payload);
        onSaved("Allocation added.");
      }
      onClose();
    } catch (e) {
      onError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-3 max-h-[90vh] overflow-y-auto">
        <h3 className="font-semibold">{editing ? "Edit allocation" : "Add allocation"}</h3>

        <label className="flex items-center gap-2 text-sm">
          <input
            type="checkbox"
            checked={form.unassigned}
            onChange={(e) =>
              setForm((prev) => ({
                ...prev,
                unassigned: e.target.checked,
                faculty_id: e.target.checked ? "" : prev.faculty_id,
              }))
            }
          />
          Unassigned / placeholder (not offered)
        </label>

        {!form.unassigned ? (
          <select
            className="w-full border rounded-lg px-3 py-2 text-sm"
            value={form.faculty_id}
            onChange={(e) => {
              const faculty = eceFaculty.find((f) => String(f.id) === e.target.value);
              setForm((prev) => ({
                ...prev,
                faculty_id: e.target.value,
                faculty_name: faculty?.name ?? "",
                unassigned: false,
              }));
            }}
          >
            <option value="">Select faculty</option>
            {eceFaculty.map((f) => (
              <option key={f.id} value={f.id}>
                {f.name}
              </option>
            ))}
          </select>
        ) : (
          <input
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Placeholder label (optional)"
            value={form.faculty_name}
            onChange={(e) => setForm((prev) => ({ ...prev, faculty_name: e.target.value }))}
          />
        )}

        <input
          className="w-full border rounded-lg px-3 py-2 text-sm"
          placeholder="Semester (e.g. Monsoon 2026)"
          value={form.semester}
          onChange={(e) => {
            const semester = e.target.value;
            setForm((prev) => ({
              ...prev,
              semester,
              academic_year: academicYearForSemester(semester) || prev.academic_year,
            }));
          }}
        />
        <input
          className="w-full border rounded-lg px-3 py-2 text-sm"
          placeholder="Academic year (e.g. 2026-27)"
          value={form.academic_year}
          onChange={(e) => setForm((prev) => ({ ...prev, academic_year: e.target.value }))}
        />

        <select
          className="w-full border rounded-lg px-3 py-2 text-sm"
          value={form.course_catalog_id}
          onChange={(e) => applyCatalog(e.target.value)}
        >
          <option value="">Course from catalog (optional)</option>
          {catalog.map((c) => (
            <option key={c.id} value={c.id}>
              {c.course_code}: {c.course_name}
            </option>
          ))}
        </select>

        <input
          className="w-full border rounded-lg px-3 py-2 text-sm"
          placeholder="Course code"
          value={form.course_code}
          onChange={(e) => setForm((prev) => ({ ...prev, course_code: e.target.value }))}
        />
        <input
          className="w-full border rounded-lg px-3 py-2 text-sm"
          placeholder="Course name"
          value={form.course_name}
          onChange={(e) => setForm((prev) => ({ ...prev, course_name: e.target.value }))}
        />

        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-xs text-slate-500">UG type</label>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={form.ug_type}
              onChange={(e) => setForm((prev) => ({ ...prev, ug_type: e.target.value }))}
            >
              {TYPE_OPTIONS.map((t) => (
                <option key={t || "none"} value={t}>
                  {t || "— (not UG)"}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500">PG type</label>
            <select
              className="w-full border rounded-lg px-3 py-2 text-sm"
              value={form.pg_type}
              onChange={(e) => setForm((prev) => ({ ...prev, pg_type: e.target.value }))}
            >
              {TYPE_OPTIONS.map((t) => (
                <option key={t || "none"} value={t}>
                  {t || "— (not PG)"}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label className="text-xs text-slate-500">No. of registered students</label>
          <input
            type="number"
            min={0}
            className="w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="Leave blank if unknown"
            value={form.registered_students}
            onChange={(e) => setForm((prev) => ({ ...prev, registered_students: e.target.value }))}
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={onClose} disabled={busy}>
            Cancel
          </button>
          <button
            type="button"
            className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50"
            onClick={save}
            disabled={busy}
          >
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
