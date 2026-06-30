function academicYearForSemester(semester: string): string {
  const parts = semester.trim().split(" ");
  if (parts.length !== 2) return "";
  const term = parts[0];
  const year = parseInt(parts[1], 10);
  if (Number.isNaN(year)) return "";
  if (term.toLowerCase() === "monsoon") return `${year}-${String(year + 1).slice(-2)}`;
  return `${year - 1}-${String(year).slice(-2)}`;
}

/**
 * True chronological sort key — matches backend ``semester_sort_key``.
 * Within a calendar year terms run Winter (Jan–May) → Summer (May–Jul) →
 * Monsoon (Aug–Dec), so Winter 2023 precedes Monsoon 2023. This yields
 * academic-year grouping: Monsoon 2022 → Winter 2023, then Monsoon 2023 →
 * Winter 2024, and so on.
 */
function semesterSortKey(tag: string): [number, number] {
  const parts = tag.trim().split(" ");
  if (parts.length < 2) return [0, 0];
  const term = parts[0].toLowerCase();
  const year = parseInt(parts[parts.length - 1], 10);
  if (Number.isNaN(year)) return [0, 0];
  const order: Record<string, number> = { winter: 1, summer: 2, monsoon: 3 };
  return [year, order[term] ?? 0];
}

function compareSemestersChronological(a: string, b: string): number {
  const [ay, at] = semesterSortKey(a);
  const [by, bt] = semesterSortKey(b);
  if (ay !== by) return ay - by;
  return at - bt;
}

function sortBySemesterChronological<T>(items: T[], getSemester: (item: T) => string): T[] {
  return [...items].sort((a, b) => compareSemestersChronological(getSemester(a), getSemester(b)));
}

function isSemesterInRange(tag: string, fromSemester: string, toSemester: string): boolean {
  const key = semesterSortKey(tag);
  const fromKey = semesterSortKey(fromSemester);
  const toKey = semesterSortKey(toSemester);
  const lo = fromKey[0] < toKey[0] || (fromKey[0] === toKey[0] && fromKey[1] <= toKey[1]) ? fromKey : toKey;
  const hi = lo === fromKey ? toKey : fromKey;
  return (
    (key[0] > lo[0] || (key[0] === lo[0] && key[1] >= lo[1])) &&
    (key[0] < hi[0] || (key[0] === hi[0] && key[1] <= hi[1]))
  );
}

export {
  academicYearForSemester,
  compareSemestersChronological,
  isSemesterInRange,
  semesterSortKey,
  sortBySemesterChronological,
};
