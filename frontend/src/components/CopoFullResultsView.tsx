const PO_HEADERS = [
  ...Array.from({ length: 12 }, (_, i) => `PO${i + 1}`),
  "PSO1",
  "PSO2",
  "PSO3",
];

type CoStats = {
  mean?: Record<string, number>;
  std?: Record<string, number>;
  threshold?: Record<string, number>;
  pct_above?: Record<string, number>;
};

type Props = {
  courseTitle: string;
  courseFilename?: string;
  mappingFilename?: string;
  uniqueCos: string[];
  intermediate: Record<string, unknown>;
  scopeSummary?: string;
};

function groupAssessmentIds(ids: string[]): { parent: string; children: string[] }[] {
  const groups = new Map<string, string[]>();
  for (const id of ids) {
    if (/_bonus$/i.test(id) || /^bonus/i.test(id)) continue;
    const dot = id.indexOf(".");
    if (dot > 0) {
      const parent = id.slice(0, dot);
      groups.set(parent, [...(groups.get(parent) ?? []), id]);
    } else {
      // Standalone component used in CO attainment (e.g. Project with CO mapping).
      groups.set(id, [id]);
    }
  }
  return Array.from(groups.entries()).map(([parent, children]) => ({
    parent,
    children: [...children].sort((a, b) => {
      const na = Number(a.slice(a.indexOf(".") + 1));
      const nb = Number(b.slice(b.indexOf(".") + 1));
      if (!Number.isNaN(na) && !Number.isNaN(nb)) return na - nb;
      return a.localeCompare(b);
    }),
  }));
}

function mappingCellClass(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return "";
  if (value >= 3) return "bg-rose-100";
  if (value >= 2) return "bg-orange-100";
  if (value >= 1) return "bg-yellow-100";
  return "bg-sky-50";
}

/** Full attainment report sections (legacy portal parity). */
export default function CopoFullResultsView({
  courseFilename,
  mappingFilename,
  uniqueCos,
  intermediate,
  scopeSummary,
}: Props) {
  const assessmentIds = (intermediate.assessment_ids as string[]) || [];
  const coStats = (intermediate.CO_stats as CoStats) || {};
  const coPoMapping = (intermediate.CO_PO_mapping as Record<string, Record<string, number>>) || {};
  const directPo =
    (intermediate.direct_po_pso_attainment as Record<string, number>) ||
    (intermediate.po_pso_attainment as Record<string, number>) ||
    {};
  const finalPo = (intermediate.final_po_pso_attainment as Record<string, number>) || null;
  const indirectCo = (intermediate.indirect_attainment_values as Record<string, number>) || {};
  const indirectPo = (intermediate.indirect_po_pso_attainment as Record<string, number>) || null;
  const hasIndirect = Object.keys(indirectCo).length > 0;

  const assessmentGroups = groupAssessmentIds(assessmentIds);
  const poCols = PO_HEADERS.filter(
    (h) =>
      directPo[h] != null ||
      (finalPo && finalPo[h] != null) ||
      Object.values(coPoMapping).some((row) => row[h] != null)
  );

  return (
    <div className="space-y-6">
      <section className="bg-white border rounded-xl p-6 space-y-3">
        <h3 className="text-sm font-bold uppercase tracking-wide text-teal-700 border-b border-teal-100 pb-2">
          Course information
        </h3>
        <dl className="grid sm:grid-cols-2 gap-3 text-sm">
          {courseFilename && (
            <div>
              <dt className="text-slate-500">Course data</dt>
              <dd className="font-medium">{courseFilename}</dd>
            </div>
          )}
          {mappingFilename && (
            <div>
              <dt className="text-slate-500">CO-PO mapping</dt>
              <dd className="font-medium">{mappingFilename}</dd>
            </div>
          )}
          {scopeSummary && (
            <div className="sm:col-span-2">
              <dt className="text-slate-500">Evaluation scope</dt>
              <dd className="font-medium">{scopeSummary}</dd>
            </div>
          )}
        </dl>
        <div>
          <p className="text-xs font-semibold uppercase text-slate-500 mb-2">Course outcomes</p>
          <div className="flex flex-wrap gap-2">
            {uniqueCos.map((co) => (
              <span
                key={co}
                className="bg-slate-900 text-white text-xs font-medium px-2.5 py-1 rounded"
              >
                {co}
              </span>
            ))}
          </div>
        </div>
        {!hasIndirect && (
          <p className="text-sm text-amber-800 bg-amber-50 border border-amber-100 rounded px-3 py-2">
            Indirect attainment not found for this course. Only direct attainment is shown.
          </p>
        )}
      </section>

      {assessmentGroups.length > 0 && (
        <section className="bg-white border rounded-xl p-6 space-y-3">
          <h3 className="text-sm font-bold uppercase tracking-wide text-teal-700 border-b border-teal-100 pb-2">
            Assessment IDs
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
            {assessmentGroups.map(({ parent, children }) => (
              <div key={parent} className="border rounded-lg p-3 bg-slate-50 text-sm">
                <p className="font-semibold text-slate-800 mb-1">{parent}</p>
                <ul className="text-xs text-slate-600 space-y-0.5">
                  {children.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="bg-white border rounded-xl p-6 overflow-x-auto">
        <h3 className="text-sm font-bold uppercase tracking-wide text-teal-700 border-b border-teal-100 pb-2 mb-3">
          CO statistics
        </h3>
        <table className="min-w-full text-sm border">
          <thead>
            <tr className="bg-slate-800 text-white">
              <th className="px-3 py-2 text-left">CO</th>
              <th className="px-3 py-2 text-right">Mean</th>
              <th className="px-3 py-2 text-right">Std dev</th>
              <th className="px-3 py-2 text-right">Threshold</th>
              <th className="px-3 py-2 text-right">% above threshold</th>
            </tr>
          </thead>
          <tbody>
            {uniqueCos.map((co) => (
              <tr key={co} className="border-t">
                <td className="px-3 py-2 font-medium">{co}</td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {coStats.mean?.[co] != null ? Number(coStats.mean[co]).toFixed(2) : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {coStats.std?.[co] != null ? Number(coStats.std[co]).toFixed(2) : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums">
                  {coStats.threshold?.[co] != null ? Number(coStats.threshold[co]).toFixed(2) : "—"}
                </td>
                <td className="px-3 py-2 text-right tabular-nums bg-green-50 font-medium">
                  {coStats.pct_above?.[co] != null
                    ? `${Number(coStats.pct_above[co]).toFixed(2)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {Object.keys(coPoMapping).length > 0 && (
        <section className="bg-white border rounded-xl p-6 overflow-x-auto">
          <h3 className="text-sm font-bold uppercase tracking-wide text-teal-700 border-b border-teal-100 pb-2 mb-3">
            CO-PO mapping
          </h3>
          <table className="min-w-full text-xs border">
            <thead>
              <tr className="bg-slate-800 text-white">
                <th className="px-2 py-1 text-left sticky left-0 bg-slate-800">CO</th>
                {poCols.map((h) => (
                  <th key={h} className="px-2 py-1 text-center whitespace-nowrap">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {uniqueCos.map((co) => (
                <tr key={co} className="border-t">
                  <td className="px-2 py-1 font-medium sticky left-0 bg-white">{co}</td>
                  {poCols.map((h) => {
                    const v = coPoMapping[co]?.[h];
                    return (
                      <td
                        key={h}
                        className={`px-2 py-1 text-center tabular-nums ${mappingCellClass(v)}`}
                      >
                        {v != null && v !== 0 ? v : ""}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <section className="bg-white border rounded-xl p-6 overflow-x-auto">
        <h3 className="text-sm font-bold uppercase tracking-wide text-teal-700 border-b border-teal-100 pb-2 mb-3">
          Direct PO/PSO attainment (from course data)
        </h3>
        <table className="min-w-full text-sm border">
          <thead>
            <tr className="bg-slate-100">
              {poCols.filter((h) => directPo[h] != null).map((h) => (
                <th key={h} className="px-2 py-1 text-right">
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {poCols.filter((h) => directPo[h] != null).map((h) => (
                <td key={h} className="px-2 py-1 text-right border-t tabular-nums">
                  {Number(directPo[h]).toFixed(2)}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </section>

      {hasIndirect && finalPo && (
        <section className="bg-white border rounded-xl p-6 overflow-x-auto space-y-4">
          <h3 className="text-sm font-bold uppercase tracking-wide text-teal-700 border-b border-teal-100 pb-2">
            Indirect &amp; final combined attainment
          </h3>
          <p className="text-xs text-slate-600">
            Final PO/PSO = 90% direct + 10% indirect (when indirect CO values were provided).
          </p>
          {indirectPo && (
            <div>
              <p className="text-xs font-medium text-slate-500 mb-1">Indirect PO/PSO</p>
              <table className="min-w-full text-sm border">
                <thead>
                  <tr className="bg-slate-100">
                    {poCols.filter((h) => indirectPo[h] != null).map((h) => (
                      <th key={h} className="px-2 py-1 text-right">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    {poCols.filter((h) => indirectPo[h] != null).map((h) => (
                      <td key={h} className="px-2 py-1 text-right border-t tabular-nums">
                        {Number(indirectPo[h]).toFixed(2)}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
          )}
          <div>
            <p className="text-xs font-medium text-slate-500 mb-1">Final PO/PSO</p>
            <table className="min-w-full text-sm border">
              <thead>
                <tr className="bg-slate-100">
                  {poCols.filter((h) => finalPo[h] != null).map((h) => (
                    <th key={h} className="px-2 py-1 text-right">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr>
                  {poCols.filter((h) => finalPo[h] != null).map((h) => (
                    <td key={h} className="px-2 py-1 text-right border-t tabular-nums font-medium">
                      {Number(finalPo[h]).toFixed(2)}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      )}

      <section className="bg-white border rounded-xl p-6 overflow-x-auto">
        <h3 className="text-sm font-bold uppercase tracking-wide text-teal-700 border-b border-teal-100 pb-2 mb-3">
          CO attainment (% above threshold)
        </h3>
        <table className="min-w-full text-sm border">
          <thead>
            <tr className="bg-slate-100">
              {uniqueCos.map((co) => (
                <th key={co} className="px-2 py-1 text-right">
                  {co}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              {uniqueCos.map((co) => (
                <td key={co} className="px-2 py-1 text-right border-t tabular-nums">
                  {coStats.pct_above?.[co] != null ? Number(coStats.pct_above[co]).toFixed(2) : "—"}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </section>
    </div>
  );
}
