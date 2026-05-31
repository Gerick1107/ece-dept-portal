/** Non-blocking CO mapping warnings returned after generate/compare. */
export default function CoWarningsBanner({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null;
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-950 space-y-1">
      <p className="font-medium">CO mapping notice</p>
      <ul className="list-disc list-inside space-y-0.5">
        {warnings.map((w) => (
          <li key={w}>{w}</li>
        ))}
      </ul>
      <p className="text-xs text-amber-800 pt-1">
        These components were excluded from CO attainment. Please verify mappings before submitting
        official reports.
      </p>
    </div>
  );
}
