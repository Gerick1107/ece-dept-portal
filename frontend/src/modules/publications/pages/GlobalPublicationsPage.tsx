import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import PublicationsTable from "../components/PublicationsTable";
import { deletePublication, listAllPublications } from "../services/publicationsApi";
import type { Publication } from "../types/publications";

export default function GlobalPublicationsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [items, setItems] = useState<Publication[]>([]);
  const [titleQuery, setTitleQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    setLoading(true);
    setError("");
    listAllPublications()
      .then(setItems)
      .catch((e) => {
        setItems([]);
        setError(e instanceof Error ? e.message : "Failed to load publications");
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const q = titleQuery.trim().toLowerCase();
    if (!q) return items;
    return items.filter((p) => p.title.toLowerCase().includes(q));
  }, [items, titleQuery]);

  async function handleDelete(publicationId: number) {
    if (!window.confirm("Delete this publication permanently? This cannot be undone.")) return;
    await deletePublication(publicationId);
    setItems((prev) => prev.filter((p) => p.id !== publicationId));
  }

  return (
    <div className="space-y-4 min-h-0 pb-8">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <h2 className="text-xl font-semibold">Global Publication Search</h2>
        <input
          className="border rounded px-3 py-2 text-sm w-80"
          placeholder="Search by title..."
          value={titleQuery}
          onChange={(e) => setTitleQuery(e.target.value)}
        />
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
            isAdmin={isAdmin}
            onDelete={isAdmin ? handleDelete : undefined}
          />
        )}
      </div>
    </div>
  );
}
