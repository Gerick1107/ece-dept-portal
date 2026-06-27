import { useCallback, useEffect, useState } from "react";
import { apiPostForm } from "../../../services/api";
import { listFaculty } from "../../publications/services/publicationsApi";
import type { Faculty } from "../../publications/types/publications";
import {
  listAllocations,
  resolveAllocationFaculty,
  type AllocationCourse,
} from "../services/courseAllocationApi";

type UploadPreview = {
  semesters: string[];
  rows: Array<Record<string, unknown>>;
  matched_count?: number;
  unmatched_names: string[];
  errors: string[];
};

type Props = {
  scope: string;
  onChanged: () => void;
};

export default function CourseAllocationAdminPanel({ scope, onChanged }: Props) {
  const [unmatched, setUnmatched] = useState<AllocationCourse[]>([]);
  const [eceFaculty, setEceFaculty] = useState<Faculty[]>([]);
  const [preview, setPreview] = useState<UploadPreview | null>(null);
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [resolveRowId, setResolveRowId] = useState<number | null>(null);
  const [resolveFacultyId, setResolveFacultyId] = useState("");

  const load = useCallback(async () => {
    try {
      const alloc = await listAllocations({ scope: scope === "all" ? "all" : scope });
      setUnmatched(alloc.unmatched ?? []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Admin load failed");
    }
  }, [scope]);

  useEffect(() => {
    load();
    listFaculty({ page: 1, page_size: 200 })
      .then((r) => setEceFaculty(r.items.filter((f) => f.department?.includes("ECE"))))
      .catch(() => {});
  }, [load]);

  async function handlePreview() {
    if (!uploadFile) return;
    setError("");
    const fd = new FormData();
    fd.append("file", uploadFile);
    try {
      const data = await apiPostForm<UploadPreview>("/course-allocation/upload/preview", fd);
      setPreview(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed");
    }
  }

  async function handleCommit() {
    if (!uploadFile) return;
    setError("");
    const fd = new FormData();
    fd.append("file", uploadFile);
    try {
      const r = await apiPostForm<{ created: number }>("/course-allocation/upload", fd);
      setMessage(`Uploaded ${r.created} allocation row(s).`);
      setPreview(null);
      setUploadFile(null);
      await load();
      onChanged();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    }
  }

  return (
    <div className="space-y-6 border-t border-slate-200 pt-6">
      <h3 className="font-semibold text-slate-800">Admin — Course Allocation</h3>
      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <section className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
        <h4 className="font-medium">Upload new-semester allocation (.xlsx)</h4>
        <input type="file" accept=".xlsx,.xls" onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)} />
        <div className="flex gap-2">
          <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={handlePreview} disabled={!uploadFile}>Preview</button>
          <button type="button" className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg" onClick={handleCommit} disabled={!uploadFile}>Commit upload</button>
        </div>
        {preview && (
          <div className="text-sm bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1">
            <p>Semesters: {preview.semesters?.join(", ") || "—"}</p>
            <p>Rows to import: {preview.rows?.length ?? 0}</p>
            {typeof preview.matched_count === "number" && (
              <p className="text-teal-800">Faculty auto-matched: {preview.matched_count}</p>
            )}
            {preview.unmatched_names?.length > 0 ? (
              <p className="text-amber-800">
                Names not auto-matched (assign manually after commit): {preview.unmatched_names.join(", ")}
              </p>
            ) : (
              <p className="text-teal-800">All faculty names matched existing records.</p>
            )}
          </div>
        )}
      </section>

      {unmatched.length > 0 && (
        <section className="bg-amber-50 border border-amber-200 rounded-xl p-4">
          <h4 className="font-medium mb-2">Unmatched faculty names ({unmatched.length})</h4>
          <ul className="text-sm space-y-2">
            {unmatched.map((u) => (
              <li key={u.id} className="flex flex-wrap items-center gap-2">
                <span>{u.faculty_name} — {u.course_code} ({u.semester})</span>
                <button type="button" className="text-xs underline text-teal-800" onClick={() => setResolveRowId(u.id)}>Match faculty</button>
              </li>
            ))}
          </ul>
        </section>
      )}

      {resolveRowId != null && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-sm w-full p-6 space-y-3">
            <h4 className="font-semibold">Match faculty name</h4>
            <select className="w-full border rounded-lg px-3 py-2 text-sm" value={resolveFacultyId} onChange={(e) => setResolveFacultyId(e.target.value)}>
              <option value="">Select faculty</option>
              {eceFaculty.map((f) => (
                <option key={f.id} value={f.id}>{f.name}</option>
              ))}
            </select>
            <div className="flex justify-end gap-2">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setResolveRowId(null)}>Cancel</button>
              <button
                type="button"
                className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg"
                onClick={async () => {
                  if (!resolveFacultyId) return;
                  await resolveAllocationFaculty(resolveRowId, Number(resolveFacultyId));
                  setResolveRowId(null);
                  setMessage("Faculty matched.");
                  await load();
                  onChanged();
                }}
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
