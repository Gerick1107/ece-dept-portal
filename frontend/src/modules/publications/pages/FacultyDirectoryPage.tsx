import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { listFaculty } from "../services/publicationsApi";
import type { Faculty } from "../types/publications";

type Tab = "current" | "former";

function FacultyCard({ faculty }: { faculty: Faculty }) {
  return (
    <Link
      to={`/publications/faculty/${faculty.id}`}
      className="bg-white border rounded-xl p-4 hover:shadow transition-shadow block"
    >
      <div className="flex items-start gap-3">
        <img
          src={faculty.photo_url || "/logo.png?v=2"}
          className="w-14 h-14 object-cover rounded-full border shrink-0"
          alt={faculty.name}
        />
        <div className="min-w-0">
          <p className="font-medium truncate">{faculty.name}</p>
          <p className="text-xs text-slate-600">{faculty.designation || "Faculty"}</p>
          <p className="text-xs text-slate-500">{faculty.department || "Department not set"}</p>
          {faculty.leave_year != null && (
            <p className="text-xs text-amber-800 mt-1">Left: {faculty.leave_year}</p>
          )}
        </div>
      </div>
      <div className="mt-3 grid grid-cols-2 text-xs text-slate-700 gap-2">
        <p>Publications: {faculty.total_publications}</p>
        <p>Citations: {faculty.total_citations}</p>
      </div>
    </Link>
  );
}

export default function FacultyDirectoryPage() {
  const [items, setItems] = useState<Faculty[]>([]);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState<Tab>("current");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    listFaculty({ page: 1, page_size: 100, include_inactive: true })
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load faculty"))
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return items.filter((f) => {
      const isFormer = f.leave_year != null;
      if (tab === "current" && isFormer) return false;
      if (tab === "former" && !isFormer) return false;
      if (q && !f.name.toLowerCase().includes(q)) return false;
      return true;
    });
  }, [items, search, tab]);

  const tabBtn = (key: Tab, label: string) => (
    <button
      type="button"
      onClick={() => setTab(key)}
      className={`px-4 py-2 text-sm rounded-lg transition-colors ${
        tab === key
          ? "bg-teal-700 text-white font-medium"
          : "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50"
      }`}
    >
      {label}
    </button>
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-xl font-semibold">Faculty Directory</h2>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search faculty by name..."
          className="border rounded-lg px-3 py-2 text-sm w-72"
        />
      </div>
      <div className="flex gap-2">
        {tabBtn("current", "Current Faculty")}
        {tabBtn("former", "Former Faculty")}
      </div>
      {error && <p className="text-sm text-red-700">{error}</p>}
      {loading ? (
        <p className="text-sm text-slate-500">Loading faculty...</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((faculty) => (
            <FacultyCard key={faculty.id} faculty={faculty} />
          ))}
          {filtered.length === 0 && (
            <p className="text-sm text-slate-500 col-span-full">No faculty match this filter.</p>
          )}
        </div>
      )}
    </div>
  );
}
