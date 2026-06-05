import type { ComparisonSetup } from "../types/copo";

/** Legacy-style comparison metadata block. */
export default function ComparisonSetupPanel({ setup }: { setup: ComparisonSetup }) {
  return (
    <section className="bg-white border rounded-xl p-6 space-y-3">
      <h3 className="text-sm font-bold uppercase tracking-wide text-teal-700 border-b border-teal-100 pb-2">
        Comparison setup
      </h3>
      <dl className="grid sm:grid-cols-2 gap-x-6 gap-y-2 text-sm min-w-0">
        <div className="min-w-0">
          <dt className="text-slate-500">Input sheet</dt>
          <dd className="font-medium break-words">{setup.input_sheet}</dd>
        </div>
        <div className="min-w-0 sm:col-span-2">
          <dt className="text-slate-500">To compare with</dt>
          <dd className="font-medium break-all text-xs leading-snug" title={setup.compare_filename}>
            {setup.compare_filename}
          </dd>
        </div>
        <div className="min-w-0">
          <dt className="text-slate-500">Mapping file</dt>
          <dd className="font-medium break-words">{setup.mapping_filename}</dd>
        </div>
        <div className="min-w-0">
          <dt className="text-slate-500">Evaluation scope</dt>
          <dd className="font-medium break-words">{setup.scope_summary}</dd>
        </div>
        <div className="sm:col-span-2">
          <dt className="text-slate-500">Threshold rule</dt>
          <dd className="font-medium">{setup.threshold_rule}</dd>
        </div>
      </dl>
      <p className="text-sm text-green-800 bg-green-50 border border-green-100 rounded-lg px-4 py-3">
        {setup.delta_note ??
          "Delta is shown as Calculated − Read. A zero delta means the recomputed output matches the uploaded comparison workbook for that value."}
      </p>
    </section>
  );
}
