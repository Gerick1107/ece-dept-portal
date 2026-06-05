import { useState } from "react";
import AwardsAnalyticsTab from "../components/AwardsAnalyticsTab";
import CopoAnalyticsTab from "../components/CopoAnalyticsTab";
import ProjectsAnalyticsTab from "../components/ProjectsAnalyticsTab";
import PublicationsAnalyticsTab from "../components/PublicationsAnalyticsTab";

const TABS = [
  { id: "copo", label: "CO/PO Attainment" },
  { id: "projects", label: "BTP / IP Projects" },
  { id: "awards", label: "Faculty Awards" },
  { id: "publications", label: "Publications" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function AnalyticsPage() {
  const [tab, setTab] = useState<TabId>("copo");

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Analytics Dashboard</h2>
          <p className="text-sm text-slate-600 mt-1">
            Aggregated insights from CO/PO runs, BTP/IP projects, faculty awards, and publications.
          </p>
          <p className="text-xs text-slate-400 mt-1">Last loaded: {new Date().toLocaleString()}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-slate-200 pb-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm rounded-t-lg transition-colors ${
              tab === t.id ? "bg-white border border-b-white border-slate-200 font-medium text-teal-800 -mb-px" : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "copo" && <CopoAnalyticsTab />}
      {tab === "projects" && <ProjectsAnalyticsTab />}
      {tab === "awards" && <AwardsAnalyticsTab />}
      {tab === "publications" && <PublicationsAnalyticsTab />}
    </div>
  );
}
