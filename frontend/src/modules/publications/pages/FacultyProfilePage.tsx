import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import PublicationsTable from "../components/PublicationsTable";
import {
  deletePublication,
  listAllPublications,
  listFaculty,
  updatePublication,
} from "../services/publicationsApi";
import type {
  Faculty,
  Publication,
  PublicationEditPayload,
  PublicationSearchBy,
} from "../types/publications";
import { venueIsPreprintOrUnlisted } from "../types/publications";

type ProfileTab =
  | "publications"
  | "journals"
  | "conferences"
  | "book_chapters"
  | "books"
  | "preprints"
  | "patents";

const hasText = (v?: string | null) => Boolean(v && v.trim());

export default function FacultyProfilePage() {
  const { facultyId } = useParams();
  const { user } = useAuth();
  const id = Number(facultyId || 0);
  const canManage =
    user?.role === "admin" ||
    ((user?.role === "faculty" || user?.role === "hod") && user.faculty_id === id);
  const [faculty, setFaculty] = useState<Faculty | null>(null);
  const [publications, setPublications] = useState<Publication[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchBy, setSearchBy] = useState<PublicationSearchBy>("title");
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

  const matchesTab = useCallback((p: Publication, tab: ProfileTab) => {
    switch (tab) {
      case "patents":
        return p.is_patent;
      case "journals":
        return !p.is_patent && hasText(p.journal);
      case "conferences":
        return !p.is_patent && hasText(p.conference);
      case "book_chapters":
        return !p.is_patent && hasText(p.book);
      case "books":
        return !p.is_patent && Boolean(p.is_manual_book);
      case "preprints":
        return !p.is_patent && venueIsPreprintOrUnlisted(p);
      case "publications":
      default:
        return !p.is_patent;
    }
  }, []);

  const tabItems = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return publications.filter((p) => {
      if (!matchesTab(p, activeTab)) return false;
      if (!q) return true;
      if (searchBy === "venue") {
        const venue = `${p.journal || ""} ${p.conference || ""} ${p.book || ""} ${p.publisher || ""}`.toLowerCase();
        return venue.includes(q);
      }
      return p.title.toLowerCase().includes(q);
    });
  }, [publications, searchQuery, searchBy, activeTab, matchesTab]);

  const counts = useMemo(
    () => ({
      publications: publications.filter((p) => matchesTab(p, "publications")).length,
      journals: publications.filter((p) => matchesTab(p, "journals")).length,
      conferences: publications.filter((p) => matchesTab(p, "conferences")).length,
      book_chapters: publications.filter((p) => matchesTab(p, "book_chapters")).length,
      books: publications.filter((p) => matchesTab(p, "books")).length,
      preprints: publications.filter((p) => matchesTab(p, "preprints")).length,
      patents: publications.filter((p) => matchesTab(p, "patents")).length,
    }),
    [publications, matchesTab]
  );

  const scholarUrl = useMemo(
    () => (faculty ? `https://scholar.google.com/citations?user=${faculty.scholar_id}` : "#"),
    [faculty]
  );

  async function handleDelete(publicationId: number) {
    await deletePublication(publicationId);
    setPublications((prev) => prev.filter((p) => p.id !== publicationId));
  }

  async function handleEdit(publicationId: number, payload: PublicationEditPayload) {
    const updated = await updatePublication(publicationId, payload);
    setPublications((prev) => prev.map((p) => (p.id === publicationId ? { ...p, ...updated } : p)));
  }

  if (!faculty) return <p className="text-sm text-slate-500">Loading faculty profile...</p>;

  return (
    <div className="space-y-6 min-h-0">
      <section className="bg-white border rounded-xl p-5">
        <div className="flex items-start gap-4">
          <img src={faculty.photo_url || "/logo.png?v=2"} alt={faculty.name} className="w-20 h-20 rounded-full border" />
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
          <div className="flex gap-2 flex-wrap">
            {(
              [
                ["publications", "Publications"],
                ["journals", "Journals"],
                ["conferences", "Conferences"],
                ["book_chapters", "Book Chapters"],
                ["books", "Books"],
                ["preprints", "Preprints & Unlisted"],
                ["patents", "Patents"],
              ] as const
            ).map(([tab, label]) => (
              <button
                key={tab}
                type="button"
                onClick={() => setActiveTab(tab)}
                className={`rounded-lg px-3 py-1.5 text-sm ${
                  activeTab === tab ? "bg-teal-700 text-white" : "border border-slate-300"
                }`}
              >
                {label} ({counts[tab]})
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <select
              className="border rounded px-2 py-1 text-sm"
              value={searchBy}
              onChange={(e) => setSearchBy(e.target.value as PublicationSearchBy)}
              aria-label="Search by"
            >
              <option value="title">Search by title</option>
              <option value="venue">Search by venue</option>
            </select>
            <input
              className="border rounded px-2 py-1 text-sm w-64"
              placeholder={searchBy === "venue" ? "Search by venue..." : "Search by title..."}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>
        {activeTab === "books" && (
          <p className="text-xs text-slate-600 bg-slate-50 border rounded-lg px-3 py-2">
            The Books tab is filled only when faculty or admin assign a publication via Edit. Scholar
            sync never adds rows here automatically. Book chapters from Scholar remain under Book
            Chapters.
          </p>
        )}
        {activeTab === "preprints" && (
          <p className="text-xs text-slate-600 bg-slate-50 border rounded-lg px-3 py-2">
            Shows publications whose venue mentions arXiv, plus entries with an empty venue/journal.
          </p>
        )}
        <PublicationsTable
          publications={tabItems}
          mode={activeTab === "patents" ? "patents" : "publications"}
          venueLabel={
            activeTab === "journals"
              ? "Journal"
              : activeTab === "conferences"
                ? "Conference"
                : activeTab === "book_chapters"
                  ? "Book Chapter"
                  : activeTab === "books"
                    ? "Venue / Journal"
                    : "Venue / Journal"
          }
          venueField={
            activeTab === "journals"
              ? "journal"
              : activeTab === "conferences"
                ? "conference"
                : activeTab === "book_chapters"
                  ? "book"
                  : undefined
          }
          showPatentOffice
          canManage={canManage}
          onDelete={canManage ? handleDelete : undefined}
          onEdit={canManage ? handleEdit : undefined}
        />
      </section>
    </div>
  );
}
