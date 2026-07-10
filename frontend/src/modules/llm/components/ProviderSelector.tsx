import type { LlmProviderId, LlmProviderInfo } from "../services/llmInsightsApi";

type Props = {
  provider: LlmProviderId;
  onChange: (next: LlmProviderId) => void;
  providers: LlmProviderInfo[];
  disabled?: boolean;
  className?: string;
};

const FALLBACK: Record<LlmProviderId, string> = {
  local: "Local (Offline — free, runs on this machine)",
};

/**
 * Local LLM status indicator shown before any LLM action runs.
 * The portal runs a single local (offline) model, so this surfaces whether the
 * model is reachable rather than offering a provider choice.
 */
export default function ProviderSelector({
  provider,
  onChange,
  providers,
  disabled,
  className,
}: Props) {
  const options: LlmProviderId[] = ["local"];
  const info = providers.find((p) => p.id === provider) ?? null;
  const labelFor = (_id: LlmProviderId) => "Local (Offline — free, runs on this machine)";

  return (
    <div className={`text-sm ${className ?? ""}`}>
      <span className="block text-xs font-medium text-slate-500 mb-1">Local AI</span>
      <div className="flex flex-wrap gap-2">
        {options.map((id) => {
          const p = providers.find((x) => x.id === id);
          const active = provider === id;
          const unavailable = p ? !p.available : false;
          return (
            <button
              key={id}
              type="button"
              disabled={disabled}
              onClick={() => onChange(id)}
              title={p?.message ?? FALLBACK[id]}
              className={[
                "px-3 py-1.5 rounded-lg border text-xs transition-colors",
                active
                  ? "bg-teal-700 text-white border-teal-700"
                  : "bg-white text-slate-700 border-slate-300 hover:bg-slate-50",
                disabled ? "opacity-50 cursor-not-allowed" : "",
              ].join(" ")}
            >
              <span className="flex items-center gap-1.5">
                <span
                  aria-hidden
                  className={[
                    "inline-block w-1.5 h-1.5 rounded-full",
                    p ? (p.available ? "bg-emerald-400" : "bg-rose-400") : "bg-slate-300",
                  ].join(" ")}
                />
                {labelFor(id)}
                {unavailable ? " · offline" : ""}
              </span>
            </button>
          );
        })}
      </div>
      {info && !info.available && (
        <p className="text-xs text-amber-800 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5 mt-2">
          {info.message}
        </p>
      )}
    </div>
  );
}
