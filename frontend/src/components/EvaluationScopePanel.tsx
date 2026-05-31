import { PROGRAMME_LABELS } from "../types/copo";
import type { MarksParsePreview } from "../types/copo";

type Props = {
  preview: MarksParsePreview;
  programmes: string[];
  branches: string[];
  onProgrammesChange: (next: string[]) => void;
  onBranchesChange: (next: string[]) => void;
  stepNumber?: number;
};

/** Reusable evaluation scope UI (programme tree, branches, CO badges). */
export default function EvaluationScopePanel({
  preview,
  programmes,
  branches,
  onProgrammesChange,
  onBranchesChange,
  stepNumber,
}: Props) {
  const progKeys = Object.keys(preview.programmes);
  const branchEntries = Object.entries(preview.branches);

  function toggleProgramme(prog: string, checked: boolean) {
    if (checked) {
      onProgrammesChange([...programmes, prog]);
      const related = branchEntries
        .filter(([, info]) => info.programme === prog)
        .map(([k]) => k);
      onBranchesChange([...new Set([...branches, ...related])]);
    } else {
      onProgrammesChange(programmes.filter((p) => p !== prog));
      onBranchesChange(branches.filter((k) => preview.branches[k]?.programme !== prog));
    }
  }

  function toggleBranch(key: string, checked: boolean) {
    if (checked) {
      onBranchesChange([...branches, key]);
      const prog = preview.branches[key]?.programme;
      if (prog && !programmes.includes(prog)) {
        onProgrammesChange([...programmes, prog]);
      }
    } else {
      onBranchesChange(branches.filter((b) => b !== key));
    }
  }

  return (
    <section className="bg-white border rounded-xl p-6 space-y-4">
      <h3 className="font-medium flex items-center gap-2 text-teal-800">
        {stepNumber != null && (
          <span className="bg-teal-700 text-white w-6 h-6 rounded-full text-xs flex items-center justify-center shrink-0">
            {stepNumber}
          </span>
        )}
        Evaluation scope
      </h3>

      <div className="rounded-lg bg-sky-50 border border-sky-100 px-4 py-2 text-sm text-sky-900">
        <strong>{preview.total_students}</strong> students detected in file
      </div>

      {!preview.has_branch_data && progKeys.length > 0 && (
        <div className="rounded-lg bg-sky-50 border border-sky-100 px-4 py-2 text-xs text-sky-800">
          No branch column found in file. Branch-level filtering is unavailable; filtering stays at
          programme level.
        </div>
      )}

      <div className="space-y-3 text-sm border rounded-lg p-4 bg-slate-50/50">
        {progKeys.map((prog) => {
          const progBranches = branchEntries.filter(([, info]) => info.programme === prog);
          const label = PROGRAMME_LABELS[prog] ?? prog;
          const count = preview.programmes[prog] ?? 0;
          return (
            <div key={prog} className="space-y-1">
              <label className="flex items-center gap-2 font-medium cursor-pointer">
                <input
                  type="checkbox"
                  checked={programmes.includes(prog)}
                  onChange={(e) => toggleProgramme(prog, e.target.checked)}
                  className="rounded border-slate-300"
                />
                <span>
                  {label} <span className="text-slate-500 font-normal">({count})</span>
                </span>
              </label>
              {progBranches.length > 0 && (
                <ul className="ml-6 space-y-1 border-l-2 border-teal-200 pl-3">
                  {progBranches.map(([key, info]) => (
                    <li key={key}>
                      <label className="flex items-center gap-2 cursor-pointer text-slate-700">
                        <input
                          type="checkbox"
                          checked={branches.includes(key)}
                          onChange={(e) => toggleBranch(key, e.target.checked)}
                          className="rounded border-slate-300"
                        />
                        Branch: {info.branch}{" "}
                        <span className="text-slate-500">({info.count})</span>
                      </label>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          );
        })}
      </div>

      {preview.cos.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            Detected COs in file
          </p>
          <div className="flex flex-wrap gap-2">
            {preview.cos.map((co) => (
              <span
                key={co}
                className="inline-block bg-slate-900 text-white text-xs font-medium px-2.5 py-1 rounded"
              >
                {co}
              </span>
            ))}
          </div>
        </div>
      )}

      <p className="text-xs text-slate-500">
        Only students from selected programmes/branches are included. Default: all detected groups
        selected.
      </p>
    </section>
  );
}
