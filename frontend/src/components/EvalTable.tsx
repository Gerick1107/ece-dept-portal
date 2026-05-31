export type EvalTableData = {
  title: string;
  matched_label?: string;
  columns: string[];
  rows: { label: string; kind: string; values: (number | null)[] }[];
};

export default function EvalTable({ table }: { table: EvalTableData }) {
  return (
    <div className="overflow-x-auto border border-slate-200 rounded-lg">
      <div className="bg-slate-800 text-white px-3 py-2 text-sm font-medium">{table.title}</div>
      {table.matched_label && (
        <p className="text-xs text-slate-500 px-3 py-1 border-b bg-slate-50">
          Matched: {table.matched_label}
        </p>
      )}
      <table className="min-w-full text-xs">
        <thead>
          <tr className="bg-slate-100">
            <th className="px-2 py-1 text-left sticky left-0 bg-slate-100">Row</th>
            {table.columns.map((c) => (
              <th key={c} className="px-2 py-1 text-right whitespace-nowrap">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr
              key={row.label}
              className={`border-t ${
                row.kind === "delta" ? "bg-amber-50" : row.kind === "calculated" ? "bg-white" : "bg-slate-50"
              }`}
            >
              <td className="px-2 py-1 font-medium sticky left-0 bg-inherit">{row.label}</td>
              {row.values.map((v, i) => {
                const isZeroDelta =
                  row.kind === "delta" && v != null && Math.abs(Number(v)) < 0.00005;
                return (
                  <td
                    key={i}
                    className={`px-2 py-1 text-right tabular-nums ${
                      isZeroDelta ? "bg-green-100 font-medium" : ""
                    }`}
                  >
                    {v == null ? "—" : Number(v).toFixed(4)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
