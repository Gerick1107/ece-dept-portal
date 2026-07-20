import { useState } from "react";
import QuestionPapersTab from "../components/QuestionPapersTab";
import GradeSummaryTab from "../components/GradeSummaryTab";

const TABS = [
  { id: "question-papers", label: "Question Papers" },
  { id: "grade-summary", label: "Grade Summary" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function ModerationPage() {
  const [tab, setTab] = useState<TabId>("question-papers");

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-900">Moderation</h2>
        <p className="text-sm text-slate-600 mt-1">
          Upload and review question papers, and define grading criteria per course.
        </p>
      </div>

      <div className="flex flex-wrap gap-1 border-b border-slate-200 pb-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm rounded-t-lg transition-colors ${
              tab === t.id
                ? "bg-white border border-b-white border-slate-200 font-medium text-teal-800 -mb-px"
                : "text-slate-600 hover:bg-slate-100"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "question-papers" && <QuestionPapersTab />}
      {tab === "grade-summary" && <GradeSummaryTab />}
    </div>
  );
}