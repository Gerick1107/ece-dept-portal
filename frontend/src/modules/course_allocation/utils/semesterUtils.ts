function academicYearForSemester(semester: string): string {
  const parts = semester.trim().split(" ");
  if (parts.length !== 2) return "";
  const term = parts[0];
  const year = parseInt(parts[1], 10);
  if (Number.isNaN(year)) return "";
  if (term.toLowerCase() === "monsoon") return `${year}-${String(year + 1).slice(-2)}`;
  return `${year - 1}-${String(year).slice(-2)}`;
}

export { academicYearForSemester };
