import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import PublicationsTable from "../components/PublicationsTable";
import {
  deletePublication,
  listAllPublications,
  updatePublication,
} from "../services/publicationsApi";
import type {
  Publication,
  PublicationEditPayload,
  PublicationSearchBy,
  PublicationTableMode,
} from "../types/publications";

type RecordFilter = "all" | "publications" | "patents";

export default function GlobalPublicationsPage() {
  const { user } = useAuth();
  const canManage = user?.role === "admin" || user?.role === "faculty" || user?.role === "hod";
  const [items, setItems] = useState<Publication[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchBy, setSearchBy] = useState<PublicationSearchBy>("title");
  const [recordFilter, setRecordFilter] = useState<RecordFilter>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    const isPatent =
      recordFilter === "publications" ? false : recordFilter === "patents" ? true : undefined;
    listAllPublications(isPatent === undefined ? {} : { is_patent: isPatent })
      .then(setItems)
      .catch((e) => {
        setItems([]);
        setError(e instanceof Error ? e.message : "Failed to load publications");
      })
      .finally(() => setLoading(false));
  }, [recordFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return items;
    return items.filter((p) => {
      if (searchBy === "venue") {
        const venue = `${p.journal || ""} ${p.conference || ""} ${p.book || ""} ${p.publisher || ""}`.toLowerCase();
        return venue.includes(q);
      }
      return p.title.toLowerCase().includes(q);
    });
  }, [items, searchQuery, searchBy]);

  const tableMode: PublicationTableMode =
    recordFilter === "patents" ? "patents" : recordFilter === "publications" ? "publications" : "all";

  async function handleDelete(publicationId: number) {
    await deletePublication(publicationId);
    setItems((prev) => prev.filter((p) => p.id !== publicationId));
  }

  async function handleEdit(publicationId: number, payload: PublicationEditPayload) {
    const updated = await updatePublication(publicationId, payload);
    setItems((prev) => prev.map((p) => (p.id === publicationId ? { ...p, ...updated } : p)));
  }

  return (
    <div className="space-y-4 min-h-0 pb-8">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="text-xl font-semibold">Global Publication Search</h2>
        <div className="flex items-center gap-2 flex-wrap">
          <div className="flex rounded-lg border border-slate-300 overflow-hidden text-sm">
            {(
              [
                ["all", "All"],
                ["publications", "Publications"],
                ["patents", "Patents"],
              ] as const
            ).map(([value, label]) => (
              <button
                key={value}
                type="button"
                onClick={() => setRecordFilter(value)}
                className={`px-3 py-1.5 ${
                  recordFilter === value ? "bg-teal-700 text-white" : "bg-white text-slate-700"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
          <select
            className="border rounded px-2 py-2 text-sm"
            value={searchBy}
            onChange={(e) => setSearchBy(e.target.value as PublicationSearchBy)}
            aria-label="Search by"
          >
            <option value="title">Search by title</option>
            <option value="venue">Search by venue</option>
          </select>
          <input
            className="border rounded px-3 py-2 text-sm w-80"
            placeholder={searchBy === "venue" ? "Search by venue..." : "Search by title..."}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>
      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
      )}
      <div className="bg-white border rounded-xl p-4">
        {loading ? (
          <p className="text-sm text-slate-500">Loading publications… (fetching all pages, may take a moment)</p>
        ) : (
          <PublicationsTable
            publications={filtered}
            mode={tableMode}
            showPatentOffice={false}
            canManage={canManage}
            onDelete={canManage ? handleDelete : undefined}
            onEdit={canManage ? handleEdit : undefined}
          />
        )}
      </div>
    </div>
  );
}
