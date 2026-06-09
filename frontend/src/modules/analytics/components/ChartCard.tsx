import { useRef } from "react";
import { toPng } from "html-to-image";

type Props = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
};

export function ChartCard({ title, subtitle, children, className = "" }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  async function exportPng() {
    if (!ref.current) return;
    const dataUrl = await toPng(ref.current, { backgroundColor: "#ffffff", pixelRatio: 2 });
    const a = document.createElement("a");
    a.href = dataUrl;
    a.download = `${title.replace(/\s+/g, "_").toLowerCase()}.png`;
    a.click();
  }

  return (
    <div className={`bg-white border border-slate-200 rounded-xl shadow-sm ${className}`}>
      <div className="flex items-start justify-between gap-2 px-4 py-3 border-b border-slate-100">
        <div>
          <h4 className="font-medium text-slate-800">{title}</h4>
          {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
        </div>
        <button
          type="button"
          onClick={exportPng}
          className="text-xs px-2 py-1 rounded border border-slate-200 text-slate-600 hover:bg-slate-50 shrink-0"
        >
          PNG
        </button>
      </div>
      <div ref={ref} className="p-4" aria-label={title}>
        {children}
      </div>
    </div>
  );
}

export function KpiCard({ label, value, hint }: { label: string; value: string | number; hint?: string }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <p className="text-2xl font-semibold text-teal-800">{value}</p>
      <p className="text-sm text-slate-600 mt-1">{label}</p>
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  );
}

export { CHART_COLORS, divergingCellStyle, divergingColor, getColours } from "../utils/chartColours";
