import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { fetchFacultyAffiliations } from "../services/publicationsApi";
import type { FacultyAffiliation } from "../types/publications";

const CATEGORY_LABELS: Record<string, string> = {
  centre: "Research Centres",
  group: "Research Groups",
  lab: "Research Labs",
};

const CATEGORY_ORDER = ["centre", "group", "lab"];

export default function FacultyAffiliationsPage() {
  const { facultyId } = useParams();
  const id = Number(facultyId || 0);
  const [facultyName, setFacultyName] = useState("");
  const [items, setItems] = useState<FacultyAffiliation[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchFacultyAffiliations(id)
      .then((r) => {
        setFacultyName(r.faculty_name);
        setItems(r.items);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load affiliations"))
      .finally(() => setLoading(false));
  }, [id]);

  const grouped = useMemo(() => {
    const map = new Map<string, FacultyAffiliation[]>();
    for (const item of items) {
      const list = map.get(item.category) ?? [];
      list.push(item);
      map.set(item.category, list);
    }
    return CATEGORY_ORDER.filter((c) => map.has(c)).map((category) => ({
      category,
      label: CATEGORY_LABELS[category] ?? category,
      items: map.get(category) ?? [],
    }));
  }, [items]);

  if (loading) return <p className="text-sm text-slate-500">Loading affiliations…</p>;

  return (
    <div className="space-y-6">
      <div>
        <Link to={`/publications/faculty/${id}`} className="text-sm text-teal-700 hover:underline">
          ← Back to {facultyName || "faculty profile"}
        </Link>
        <h2 className="text-xl font-semibold mt-2">Affiliations — {facultyName}</h2>
        <p className="text-sm text-slate-600 mt-1">
          Research centres, groups, and labs this faculty member is affiliated with.
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
      )}

      {!error && !items.length && (
        <p className="text-sm text-slate-500 bg-white border rounded-xl p-6">No affiliations recorded for this faculty member.</p>
      )}

      {grouped.map((section) => (
        <section key={section.category} className="bg-white border rounded-xl p-5 space-y-3">
          <h3 className="font-medium text-slate-800">{section.label}</h3>
          <ul className="space-y-2">
            {section.items.map((item) => (
              <li key={item.id}>
                <a
                  href={item.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-teal-700 hover:underline"
                >
                  {item.name}
                </a>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
