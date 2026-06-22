import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import PublicationsTable from "../components/PublicationsTable";
import { deletePublication, listAllPublications, listFaculty } from "../services/publicationsApi";
import type { Faculty, Publication } from "../types/publications";

type ProfileTab = "publications" | "patents";

export default function FacultyProfilePage() {
  const { facultyId } = useParams();
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const id = Number(facultyId || 0);
  const [faculty, setFaculty] = useState<Faculty | null>(null);
  const [publications, setPublications] = useState<Publication[]>([]);
  const [titleQuery, setTitleQuery] = useState("");
  const [activeTab, setActiveTab] = useState<ProfileTab>("publications");
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!id) return;
    listFaculty({ include_inactive: true, page_size: 200 }).then((r) =>
      setFaculty(r.items.find((x) => x.id === id) || null)
    );
  }, [id]);

  const loadPublications = useCallback(() => {
    if (!id) return;
    setLoadError("");
    listAllPublications({ faculty_id: id })
      .then(setPublications)
      .catch((e) => {
        setPublications([]);
        setLoadError(e instanceof Error ? e.message : "Failed to load publications");
      });
  }, [id]);

  useEffect(() => {
    loadPublications();
  }, [loadPublications]);

  const tabItems = useMemo(() => {
    const q = titleQuery.trim().toLowerCase();
    const byPatent = activeTab === "patents";
    return publications.filter((p) => {
      if (p.is_patent !== byPatent) return false;
      if (!q) return true;
      return p.title.toLowerCase().includes(q);
    });
  }, [publications, titleQuery, activeTab]);

  const pubCount = useMemo(() => publications.filter((p) => !p.is_patent).length, [publications]);
  const patentCount = useMemo(() => publications.filter((p) => p.is_patent).length, [publications]);

  const scholarUrl = useMemo(
    () => (faculty ? `https://scholar.google.com/citations?user=${faculty.scholar_id}` : "#"),
    [faculty]
  );

  async function handleDelete(publicationId: number) {
    if (!window.confirm("Delete this publication permanently? This cannot be undone.")) return;
    await deletePublication(publicationId);
    setPublications((prev) => prev.filter((p) => p.id !== publicationId));
  }

  if (!faculty) return <p className="text-sm text-slate-500">Loading faculty profile...</p>;

  return (
    <div className="space-y-6 min-h-0">
      <section className="bg-white border rounded-xl p-5">
        <div className="flex items-start gap-4">
          <img src={faculty.photo_url || "/logo.png"} alt={faculty.name} className="w-20 h-20 rounded-full border" />
          <div>
            <h2 className="text-xl font-semibold">{faculty.name}</h2>
            <p className="text-sm text-slate-700">
              {faculty.designation} · {faculty.department}
            </p>
            {faculty.leave_year && (
              <p className="text-sm text-amber-800 mt-1">Left: {faculty.leave_year}</p>
            )}
            <div className="mt-2 text-sm text-slate-700">
              Citations: {faculty.total_citations} · h-index: {faculty.h_index} · i10-index: {faculty.i10_index}
            </div>
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
              {faculty.profile_link && (
                <a
                  href={faculty.profile_link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-teal-700 hover:underline"
                >
                  Institute Profile
                </a>
              )}
              <a
                href={scholarUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-teal-700 hover:underline"
              >
                Google Scholar
              </a>
              <Link to={`/publications/faculty/${id}/affiliations`} className="text-sm text-teal-700 hover:underline">
                Affiliations
              </Link>
            </div>
          </div>
        </div>
      </section>
      <section className="bg-white border rounded-xl p-5 space-y-3 flex flex-col min-h-0">
        {loadError && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{loadError}</p>
        )}
        <div className="flex justify-between items-center gap-2 flex-wrap">
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setActiveTab("publications")}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                activeTab === "publications" ? "bg-teal-700 text-white" : "border border-slate-300"
              }`}
            >
              Publications ({pubCount})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("patents")}
              className={`rounded-lg px-3 py-1.5 text-sm ${
                activeTab === "patents" ? "bg-teal-700 text-white" : "border border-slate-300"
              }`}
            >
              Patents ({patentCount})
            </button>
          </div>
          <input
            className="border rounded px-2 py-1 text-sm w-64"
            placeholder="Search by title..."
            value={titleQuery}
            onChange={(e) => setTitleQuery(e.target.value)}
          />
        </div>
        <PublicationsTable
          publications={tabItems}
          mode={activeTab === "patents" ? "patents" : "publications"}
          showPatentOffice
          isAdmin={isAdmin}
          onDelete={isAdmin ? handleDelete : undefined}
        />
      </section>
    </div>
  );
}
