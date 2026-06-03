import { useMemo, useState } from "react";
import type { Publication, PublicationTableMode } from "../types/publications";
import { publicationPeople, publicationTitleHref, publicationVenue } from "../types/publications";

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

export default function PublicationsTable({
  publications,
  mode = "publications",
  showPatentOffice = true,
  isAdmin,
  onDelete,
}: {
  publications: Publication[];
  mode?: PublicationTableMode;
  showPatentOffice?: boolean;
  isAdmin?: boolean;
  onDelete?: (id: number) => void;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("publication_year");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

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

  const patentExtraCols = mode === "patents" ? (showPatentOffice ? 2 : 1) : 0;
  const colSpan =
    (mode === "publications" ? 5 : mode === "patents" ? 4 + patentExtraCols : 4) +
    (isAdmin && onDelete ? 1 : 0);

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
                <th className="py-2 px-3 font-medium w-[20%]">Venue</th>
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
            {isAdmin && onDelete && <th className="py-2 px-2 w-10" />}
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
                    <td className="py-3 px-3 align-top text-slate-700">{publicationVenue(p) || "—"}</td>
                  </>
                ) : (
                  <td className="py-3 px-3 align-top text-slate-700 max-w-xs truncate" title={people || undefined}>
                    {people || "—"}
                  </td>
                )}
                <td className="py-3 px-3 text-center align-top">{p.publication_year ?? "—"}</td>
                <td className="py-3 px-3 text-center align-top">{p.citation_count}</td>
                {isAdmin && onDelete && (
                  <td className="py-3 px-2 text-center align-top">
                    <button
                      type="button"
                      onClick={() => onDelete(p.id)}
                      className="text-slate-400 hover:text-red-600 p-1"
                      title="Delete publication"
                      aria-label="Delete publication"
                    >
                      🗑
                    </button>
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
    </div>
  );
}
