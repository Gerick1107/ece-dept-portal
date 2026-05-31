import { useMemo, useState } from "react";

export function usePublicationsFilters() {
  const [query, setQuery] = useState("");
  const [year, setYear] = useState<number | undefined>(undefined);
  const [facultyId, setFacultyId] = useState<number | undefined>(undefined);

  const filters = useMemo(
    () => ({
      query: query || undefined,
      publication_year: year,
      faculty_id: facultyId,
    }),
    [query, year, facultyId]
  );

  return { query, setQuery, year, setYear, facultyId, setFacultyId, filters };
}
