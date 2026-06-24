import { useRef } from "react";

type Props = {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
};

export function AllocationChartCard({ title, subtitle, children, className = "" }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  return (
    <div className={`bg-white border border-slate-200 rounded-xl shadow-sm ${className}`}>
      <div className="px-4 py-3 border-b border-slate-100">
        <h4 className="font-medium text-slate-800">{title}</h4>
        {subtitle && <p className="text-xs text-slate-500 mt-0.5">{subtitle}</p>}
      </div>
      <div ref={ref} className="p-4" aria-label={title}>
        {children}
      </div>
    </div>
  );
}

export function AllocationKpiCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
      <p className="text-2xl font-semibold text-teal-800">{value}</p>
      <p className="text-sm text-slate-600 mt-1">{label}</p>
    </div>
  );
}

const CHART_COLORS = ["#0f766e", "#0369a1", "#7c3aed", "#c2410c", "#be123c", "#4d7c0f"];

export function allocationColours(n: number): string[] {
  return Array.from({ length: n }, (_, i) => CHART_COLORS[i % CHART_COLORS.length]);
}
