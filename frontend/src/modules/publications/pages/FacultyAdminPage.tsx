import { useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { apiPostJson } from "../../../services/api";

type FacultyForm = {
  name: string;
  designation: string;
  department: string;
  scholar_id: string;
  join_year: string;
  leave_year: string;
  photo_url: string;
  profile_link: string;
};

const EMPTY: FacultyForm = {
  name: "",
  designation: "",
  department: "ECE",
  scholar_id: "",
  join_year: "",
  leave_year: "",
  photo_url: "",
  profile_link: "",
};

export default function FacultyAdminPage() {
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.role === "admin";
  const [form, setForm] = useState<FacultyForm>(EMPTY);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  if (authLoading) return <p className="text-sm text-slate-500">Loading…</p>;
  if (!isAdmin) return <p className="text-sm text-slate-600">Admin access required.</p>;

  function update<K extends keyof FacultyForm>(key: K, value: FacultyForm[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setMessage("");
    setError("");
    try {
      const joinYear = Number(form.join_year);
      if (!Number.isFinite(joinYear)) {
        throw new Error("Join year must be a number");
      }
      const leaveYear = form.leave_year.trim() ? Number(form.leave_year.trim()) : null;
      if (form.leave_year.trim() && !Number.isFinite(leaveYear)) {
        throw new Error("Leave year must be a number");
      }
      const created = await apiPostJson<{ id: number; name: string }>("/publications/faculty", {
        name: form.name.trim(),
        designation: form.designation.trim() || null,
        department: form.department.trim() || null,
        scholar_id: form.scholar_id.trim(),
        join_year: joinYear,
        leave_year: leaveYear,
        photo_url: form.photo_url.trim() || null,
        profile_link: form.profile_link.trim() || null,
      });
      setMessage(
        `Added ${created.name} (id ${created.id}). The faculty directory, database, and faculty_master.csv were updated.`
      );
      setForm(EMPTY);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add faculty");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4 max-w-3xl">
      <div>
        <h2 className="text-xl font-semibold">Faculty Admin</h2>
        <p className="text-sm text-slate-600 mt-1">
          Add faculty members through the portal. Required fields match{" "}
          <code className="text-xs bg-slate-100 px-1 rounded">faculty_master.csv</code>. New entries
          appear in the Faculty Directory and are included in publication sync / filters.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="bg-white border rounded-xl p-5 space-y-4">
        <div className="grid md:grid-cols-2 gap-3">
          <label className="text-sm md:col-span-2">
            <span className="text-slate-600">Name *</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2"
              value={form.name}
              onChange={(e) => update("name", e.target.value)}
              required
              minLength={2}
            />
          </label>
          <label className="text-sm">
            <span className="text-slate-600">Designation</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2"
              value={form.designation}
              onChange={(e) => update("designation", e.target.value)}
            />
          </label>
          <label className="text-sm">
            <span className="text-slate-600">Department</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2"
              value={form.department}
              onChange={(e) => update("department", e.target.value)}
            />
          </label>
          <label className="text-sm md:col-span-2">
            <span className="text-slate-600">Google Scholar ID *</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2"
              value={form.scholar_id}
              onChange={(e) => update("scholar_id", e.target.value)}
              required
              minLength={3}
              placeholder="e.g. ABCdefGHIjkl or full profile URL"
            />
          </label>
          <label className="text-sm">
            <span className="text-slate-600">Join year *</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2"
              value={form.join_year}
              onChange={(e) => update("join_year", e.target.value)}
              required
              inputMode="numeric"
            />
          </label>
          <label className="text-sm">
            <span className="text-slate-600">Leave year</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2"
              value={form.leave_year}
              onChange={(e) => update("leave_year", e.target.value)}
              placeholder="Leave blank if current"
              inputMode="numeric"
            />
          </label>
          <label className="text-sm md:col-span-2">
            <span className="text-slate-600">Photo URL</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2"
              value={form.photo_url}
              onChange={(e) => update("photo_url", e.target.value)}
            />
          </label>
          <label className="text-sm md:col-span-2">
            <span className="text-slate-600">Institute profile link</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2"
              value={form.profile_link}
              onChange={(e) => update("profile_link", e.target.value)}
            />
          </label>
        </div>

        {message && (
          <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">
            {message}
          </p>
        )}
        {error && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={saving}
          className="rounded-lg bg-teal-700 text-white px-4 py-2 text-sm hover:bg-teal-800 disabled:opacity-60"
        >
          {saving ? "Saving…" : "Add faculty"}
        </button>
      </form>
    </div>
  );
}
