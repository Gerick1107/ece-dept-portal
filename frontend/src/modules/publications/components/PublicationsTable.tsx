import { useMemo, useState } from "react";
import type { Publication, PublicationEditPayload, PublicationTableMode } from "../types/publications";
import { publicationPeople, publicationTitleHref, publicationVenue } from "../types/publications";
import EditPublicationModal from "./EditPublicationModal";

type SortKey = "title" | "publication_year" | "citation_count";
type SortDir = "asc" | "desc";

const linkClass = "text-teal-700 hover:text-teal-900 hover:underline";

function SortHeader({
  label,
  active,
  direction,
  onClick,
  className = "",
}: {
  label: string;
  active: boolean;
  direction: SortDir;
  onClick: () => void;
  className?: string;
}) {
  return (
    <th className={`py-2 px-3 font-medium ${className}`}>
      <button type="button" onClick={onClick} className="inline-flex items-center gap-1 hover:text-teal-800">
        {label}
        {active && <span className="text-teal-700">{direction === "asc" ? "↑" : "↓"}</span>}
      </button>
    </th>
  );
}

function confirmDelete(): boolean {
  const first = window.confirm(
    "Delete this publication permanently?\n\nIt will be removed from the portal, database, and exports. Future Scholar syncs will not re-add it."
  );
  if (!first) return false;
  return window.confirm("Please confirm once more: delete this publication?");
}

export default function PublicationsTable({
  publications,
  mode = "publications",
  showPatentOffice = true,
  venueLabel = "Venue / Journal",
  venueField,
  canManage,
  onDelete,
  onEdit,
}: {
  publications: Publication[];
  mode?: PublicationTableMode;
  showPatentOffice?: boolean;
  venueLabel?: string;
  venueField?: "journal" | "conference" | "book";
  canManage?: boolean;
  onDelete?: (id: number) => Promise<void> | void;
  onEdit?: (id: number, payload: PublicationEditPayload) => Promise<void>;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("publication_year");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [editing, setEditing] = useState<Publication | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);

  const sorted = useMemo(() => {
    const copy = [...publications];
    copy.sort((a, b) => {
      let cmp = 0;
      if (sortKey === "title") {
        cmp = (a.title || "").localeCompare(b.title || "", undefined, { sensitivity: "base" });
      } else if (sortKey === "publication_year") {
        const ay = a.publication_year ?? -1;
        const by = b.publication_year ?? -1;
        cmp = ay - by;
      } else {
        cmp = (a.citation_count ?? 0) - (b.citation_count ?? 0);
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return copy;
  }, [publications, sortKey, sortDir]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "title" ? "asc" : "desc");
    }
  }

  async function handleDelete(id: number) {
    if (!onDelete || !confirmDelete()) return;
    setBusyId(id);
    try {
      await onDelete(id);
    } finally {
      setBusyId(null);
    }
  }

  const patentExtraCols = mode === "patents" ? (showPatentOffice ? 2 : 1) : 0;
  const colSpan =
    (mode === "publications" ? 5 : mode === "patents" ? 4 + patentExtraCols : 4) +
    (canManage && (onDelete || onEdit) ? 1 : 0);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead className="text-left text-slate-600 border-b bg-slate-50">
          <tr>
            <SortHeader
              label="Title"
              active={sortKey === "title"}
              direction={sortDir}
              onClick={() => toggleSort("title")}
              className="w-[35%] min-w-[200px]"
            />
            {mode === "patents" ? (
              <>
                <th className="py-2 px-3 font-medium w-[25%]">Inventors</th>
                <th className="py-2 px-3 font-medium">Patent Number</th>
                {showPatentOffice && <th className="py-2 px-3 font-medium">Patent Office</th>}
              </>
            ) : mode === "publications" ? (
              <>
                <th className="py-2 px-3 font-medium w-[25%]">Authors</th>
                <th className="py-2 px-3 font-medium w-[20%]">{venueLabel}</th>
              </>
            ) : (
              <th className="py-2 px-3 font-medium w-[30%]">Authors/Inventors</th>
            )}
            <SortHeader
              label="Year"
              active={sortKey === "publication_year"}
              direction={sortDir}
              onClick={() => toggleSort("publication_year")}
              className="w-20 text-center"
            />
            <SortHeader
              label="Cited By"
              active={sortKey === "citation_count"}
              direction={sortDir}
              onClick={() => toggleSort("citation_count")}
              className="w-24 text-center"
            />
            {canManage && (onDelete || onEdit) && <th className="py-2 px-2 w-24 text-center">Actions</th>}
          </tr>
        </thead>
        <tbody>
          {sorted.map((p) => {
            const href = publicationTitleHref(p);
            const people = publicationPeople(p);
            return (
              <tr key={p.id} className="border-b border-slate-100 hover:bg-slate-50/80">
                <td className="py-3 px-3 align-top break-words">
                  {href ? (
                    <a href={href} target="_blank" rel="noopener noreferrer" className={linkClass}>
                      {p.title}
                    </a>
                  ) : (
                    <span>{p.title}</span>
                  )}
                  {p.is_manual_book && mode !== "patents" && (
                    <span className="ml-2 inline-block text-[10px] uppercase tracking-wide bg-amber-100 text-amber-900 px-1.5 py-0.5 rounded">
                      Book
                    </span>
                  )}
                </td>
                {mode === "patents" ? (
                  <>
                    <td className="py-3 px-3 align-top text-slate-700 max-w-xs truncate" title={people || undefined}>
                      {people || "—"}
                    </td>
                    <td className="py-3 px-3 align-top">{p.patent_number || "—"}</td>
                    {showPatentOffice && (
                      <td className="py-3 px-3 align-top">{p.patent_office || "—"}</td>
                    )}
                  </>
                ) : mode === "publications" ? (
                  <>
                    <td className="py-3 px-3 align-top text-slate-700 max-w-xs truncate" title={people || undefined}>
                      {people || "—"}
                    </td>
                    <td className="py-3 px-3 align-top text-slate-700 whitespace-pre-line">
                      {(venueField ? p[venueField] : publicationVenue(p)) || "—"}
                    </td>
                  </>
                ) : (
                  <td className="py-3 px-3 align-top text-slate-700 max-w-xs truncate" title={people || undefined}>
                    {people || "—"}
                  </td>
                )}
                <td className="py-3 px-3 text-center align-top">{p.publication_year ?? "—"}</td>
                <td className="py-3 px-3 text-center align-top">{p.citation_count}</td>
                {canManage && (onDelete || onEdit) && (
                  <td className="py-3 px-2 text-center align-top">
                    <div className="inline-flex items-center gap-1">
                      {onEdit && (
                        <button
                          type="button"
                          onClick={() => setEditing(p)}
                          className="text-slate-500 hover:text-teal-700 p-1 text-xs"
                          title="Edit publication"
                          aria-label="Edit publication"
                          disabled={busyId === p.id}
                        >
                          Edit
                        </button>
                      )}
                      {onDelete && (
                        <button
                          type="button"
                          onClick={() => handleDelete(p.id)}
                          className="text-slate-400 hover:text-red-600 p-1"
                          title="Delete publication"
                          aria-label="Delete publication"
                          disabled={busyId === p.id}
                        >
                          🗑
                        </button>
                      )}
                    </div>
                  </td>
                )}
              </tr>
            );
          })}
          {sorted.length === 0 && (
            <tr>
              <td colSpan={colSpan} className="py-6 text-center text-slate-500">
                No publications found.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {editing && onEdit && (
        <EditPublicationModal
          publication={editing}
          onClose={() => setEditing(null)}
          onSave={async (payload) => {
            await onEdit(editing.id, payload);
          }}
        />
      )}
    </div>
  );
}
