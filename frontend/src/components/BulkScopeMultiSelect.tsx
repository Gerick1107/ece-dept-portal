import { PROGRAMME_LABELS } from "../types/copo";
import type { MarksParsePreview } from "../types/copo";

type Props = {
  preview: MarksParsePreview | null;
  programmes: string[];
  branches: string[];
  onProgrammesChange: (v: string[]) => void;
  onBranchesChange: (v: string[]) => void;
};

type ColumnProps = Props & { column: "programme" | "branch" };

/** Compact programme/branch multi-selects for bulk evaluation table rows. */
export default function BulkScopeMultiSelect({
  preview,
  programmes,
  branches,
  onProgrammesChange,
  onBranchesChange,
  column,
}: ColumnProps) {
  if (!preview) {
    return <span className="text-xs text-slate-400">—</span>;
  }

  const branchOptions = Object.entries(preview.branches).filter(([, info]) =>
    programmes.includes(info.programme)
  );

  if (column === "programme") {
    return (
      <select
        multiple
        size={Math.min(4, Math.max(2, Object.keys(preview.programmes).length))}
        className="w-full border rounded text-xs px-1 py-0.5 min-w-[120px]"
        value={programmes}
        onChange={(e) => {
          const selected = Array.from(e.target.selectedOptions, (o) => o.value);
          onProgrammesChange(selected);
          const validBranches = branches.filter((b) => {
            const prog = preview.branches[b]?.programme;
            return prog && selected.includes(prog);
          });
          onBranchesChange(validBranches);
        }}
      >
        {Object.entries(preview.programmes).map(([prog, count]) => (
          <option key={prog} value={prog}>
            {PROGRAMME_LABELS[prog] ?? prog} ({count})
          </option>
        ))}
      </select>
    );
  }

  if (!preview.has_branch_data || branchOptions.length === 0) {
    return <span className="text-xs text-slate-400">N/A</span>;
  }

  return (
    <select
      multiple
      size={Math.min(4, Math.max(2, branchOptions.length))}
      className="w-full border rounded text-xs px-1 py-0.5 min-w-[120px]"
      value={branches}
      onChange={(e) => onBranchesChange(Array.from(e.target.selectedOptions, (o) => o.value))}
    >
      {branchOptions.map(([key, info]) => (
        <option key={key} value={key}>
          {info.branch} ({info.count})
        </option>
      ))}
    </select>
  );
}
