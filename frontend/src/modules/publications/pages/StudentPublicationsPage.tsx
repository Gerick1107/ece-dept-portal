import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { apiDelete, apiGet, apiPostForm, apiPostJson } from "../../../services/api";

type StudentPublication = {
  id: number;
  title: string;
  authors: string | null;
  publication_year: number | null;
  extra_fields: Record<string, string>;
  fields: Record<string, string>;
};

type ListResponse = {
  items: StudentPublication[];
  columns: string[];
  pagination: { page: number; page_size: number; total: number };
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function StudentPublicationsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [items, setItems] = useState<StudentPublication[]>([]);
  const [columns, setColumns] = useState<string[]>(["Title", "Authors", "Years"]);
  const [titleQuery, setTitleQuery] = useState("");
  const [authorsQuery, setAuthorsQuery] = useState("");
  const [yearFilter, setYearFilter] = useState("");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [importing, setImporting] = useState(false);
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newAuthors, setNewAuthors] = useState("");
  const [newYear, setNewYear] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const qs = new URLSearchParams();
      qs.set("page", "1");
      qs.set("page_size", "200");
      qs.set("sort_dir", sortDir);
      if (titleQuery.trim()) qs.set("title", titleQuery.trim());
      if (authorsQuery.trim()) qs.set("authors", authorsQuery.trim());
      if (yearFilter.trim()) qs.set("year", yearFilter.trim());
      const data = await apiGet<ListResponse>(`/publications/student-publications?${qs}`);
      setItems(data.items || []);
      setColumns(data.columns?.length ? data.columns : ["Title", "Authors", "Years"]);
    } catch (e) {
      setItems([]);
      setError(e instanceof Error ? e.message : "Failed to load student publications");
    } finally {
      setLoading(false);
    }
  }, [titleQuery, authorsQuery, yearFilter, sortDir]);

  useEffect(() => {
    load();
  }, [load]);

  const years = useMemo(() => {
    const set = new Set<number>();
    for (const item of items) {
      if (item.publication_year != null) set.add(item.publication_year);
    }
    return Array.from(set).sort((a, b) => b - a);
  }, [items]);

  async function handleDownloadTemplate() {
    const res = await fetch(`${API_BASE}/publications/student-publications/template`, {
      headers: authHeaders(),
    });
    if (!res.ok) throw new Error("Failed to download template");
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "student_publications_template.xlsx";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleImport(file: File | null) {
    if (!file) return;
    setImporting(true);
    setMessage("");
    setError("");
    try {
      const form = new FormData();
      form.append("excel_file", file);
      const result = await apiPostForm<{
        inserted: number;
        skipped: number;
        columns: string[];
        errors: string[];
      }>("/publications/student-publications/import", form);
      setMessage(
        `Imported ${result.inserted} row(s)` +
          (result.skipped ? `, skipped ${result.skipped}` : "") +
          (result.errors?.length ? `. First errors: ${result.errors.slice(0, 3).join("; ")}` : ".")
      );
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setImporting(false);
    }
  }

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await apiPostJson("/publications/student-publications", {
        title: newTitle.trim(),
        authors: newAuthors.trim() || null,
        publication_year: newYear.trim() ? Number(newYear.trim()) : null,
        extra_fields: {},
      });
      setNewTitle("");
      setNewAuthors("");
      setNewYear("");
      setShowAdd(false);
      setMessage("Student publication added.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add entry");
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this student publication?")) return;
    if (!window.confirm("Confirm once more: permanently delete this entry?")) return;
    await apiDelete(`/publications/student-publications/${id}`);
    setItems((prev) => prev.filter((item) => item.id !== id));
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">Student Publications</h2>
          <p className="text-sm text-slate-600 mt-1">
            Shared department list (not tied to faculty Scholar sync). Search by title or authors;
            filter and sort by year. Extra Excel columns appear automatically after import.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => handleDownloadTemplate().catch((e) => setError(e.message))}
            className="rounded-lg border px-3 py-2 text-sm hover:bg-slate-50"
          >
            Download template
          </button>
          {isAdmin && (
            <>
              <label className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm hover:bg-teal-800 cursor-pointer">
                {importing ? "Importing…" : "Import Excel"}
                <input
                  type="file"
                  accept=".xlsx,.xls"
                  className="hidden"
                  disabled={importing}
                  onChange={(e) => handleImport(e.target.files?.[0] || null)}
                />
              </label>
              <button
                type="button"
                onClick={() => setShowAdd((v) => !v)}
                className="rounded-lg border px-3 py-2 text-sm hover:bg-slate-50"
              >
                {showAdd ? "Cancel" : "Add entry"}
              </button>
            </>
          )}
        </div>
      </div>

      {showAdd && isAdmin && (
        <form onSubmit={handleAdd} className="bg-white border rounded-xl p-4 grid md:grid-cols-4 gap-3">
          <input
            className="border rounded-lg px-3 py-2 text-sm md:col-span-2"
            placeholder="Title *"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            required
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Authors"
            value={newAuthors}
            onChange={(e) => setNewAuthors(e.target.value)}
          />
          <input
            className="border rounded-lg px-3 py-2 text-sm"
            placeholder="Year"
            value={newYear}
            onChange={(e) => setNewYear(e.target.value)}
          />
          <button type="submit" className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm md:col-span-4">
            Save entry
          </button>
        </form>
      )}

      <div className="bg-white border rounded-xl p-4 flex flex-wrap gap-2 items-center">
        <input
          className="border rounded-lg px-3 py-2 text-sm w-56"
          placeholder="Search title..."
          value={titleQuery}
          onChange={(e) => setTitleQuery(e.target.value)}
        />
        <input
          className="border rounded-lg px-3 py-2 text-sm w-56"
          placeholder="Search authors..."
          value={authorsQuery}
          onChange={(e) => setAuthorsQuery(e.target.value)}
        />
        <select
          className="border rounded-lg px-3 py-2 text-sm"
          value={yearFilter}
          onChange={(e) => setYearFilter(e.target.value)}
        >
          <option value="">All years</option>
          {years.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
        <button
          type="button"
          onClick={() => setSortDir((d) => (d === "desc" ? "asc" : "desc"))}
          className="rounded-lg border px-3 py-2 text-sm hover:bg-slate-50"
        >
          Year {sortDir === "desc" ? "↓" : "↑"}
        </button>
      </div>

      {message && (
        <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>
      )}
      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
      )}

      <div className="bg-white border rounded-xl p-4 overflow-x-auto">
        {loading ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : (
          <table className="w-full text-sm border-collapse min-w-[640px]">
            <thead className="text-left text-slate-600 border-b bg-slate-50">
              <tr>
                {columns.map((col) => (
                  <th key={col} className="py-2 px-3 font-medium whitespace-nowrap">
                    {col}
                  </th>
                ))}
                {isAdmin && <th className="py-2 px-3 w-16" />}
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id} className="border-b border-slate-100 hover:bg-slate-50/80">
                  {columns.map((col) => (
                    <td key={col} className="py-2 px-3 align-top break-words">
                      {item.fields?.[col] ||
                        (col === "Title"
                          ? item.title
                          : col === "Authors"
                            ? item.authors || "—"
                            : col === "Years"
                              ? item.publication_year ?? "—"
                              : item.extra_fields?.[col] || "—")}
                    </td>
                  ))}
                  {isAdmin && (
                    <td className="py-2 px-3 text-center">
                      <button
                        type="button"
                        onClick={() => handleDelete(item.id)}
                        className="text-slate-400 hover:text-red-600"
                        title="Delete"
                      >
                        🗑
                      </button>
                    </td>
                  )}
                </tr>
              ))}
              {items.length === 0 && (
                <tr>
                  <td
                    colSpan={columns.length + (isAdmin ? 1 : 0)}
                    className="py-8 text-center text-slate-500"
                  >
                    No student publications yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
