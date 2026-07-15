import { useState } from "react";
import { generateId } from "../utils/id";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

function authHeader(): Record<string, string> {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

type AnalyzedQuestion = {
  id: string;
  label: string;
  co_label: string;
  max_marks: number;
  is_bonus: boolean;
};

type AnalysisResult = {
  component_name: string;
  paper_total_marks: number;
  questions: Omit<AnalyzedQuestion, "id">[];
};

export default function QuestionPaperAnalyzerPanel() {
  const [componentName, setComponentName] = useState("");
  const [weightage, setWeightage] = useState("10");
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [questions, setQuestions] = useState<AnalyzedQuestion[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function analyzePaper() {
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("question_paper", file);
      const res = await fetch(`${API_BASE}/copo/analyze-question-paper`, {
        method: "POST",
        headers: authHeader(),
        body: form,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? "Analysis failed");
      const result = data as AnalysisResult;
      setAnalysis(result);
      if (!componentName.trim() && result.component_name) {
        setComponentName(result.component_name);
      }
      setQuestions(
        result.questions.map((q) => ({
          ...q,
          id: generateId(),
          max_marks: Number(q.max_marks) || 0,
        }))
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setBusy(false);
    }
  }

  async function downloadTemplate() {
    if (!analysis) return;
    const name = componentName.trim();
    if (!name) {
      setError("Enter a component name (e.g. MidSem, Quiz1).");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/copo/generate-from-question-paper`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({
          component_name: name,
          paper_total_marks: analysis.paper_total_marks,
          weightage: Number(weightage) || 0,
          questions: questions.map(({ label, co_label, max_marks, is_bonus }) => ({
            label,
            co_label,
            max_marks,
            is_bonus,
          })),
        }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Could not generate template");
      }
      const blob = await res.blob();
      const cd = res.headers.get("content-disposition") ?? "";
      const match = cd.match(/filename="?([^";]+)"?/i);
      const filename = match?.[1] || `${name}_marks_template.xlsx`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setBusy(false);
    }
  }

  function updateQuestion(id: string, patch: Partial<AnalyzedQuestion>) {
    setQuestions((prev) => prev.map((q) => (q.id === id ? { ...q, ...patch } : q)));
  }

  const scaledPreview =
    analysis && Number(weightage) > 0 && analysis.paper_total_marks > 0
      ? (Number(weightage) / analysis.paper_total_marks).toFixed(3)
      : null;

  return (
    <details className="bg-white border border-slate-200 rounded-xl group">
      <summary className="cursor-pointer list-none px-6 py-4 font-medium text-slate-900 flex items-center justify-between gap-2">
        <span>Question paper → component template (LLM)</span>
        <span className="text-xs text-teal-700 font-medium group-open:hidden">Show</span>
        <span className="text-xs text-teal-700 font-medium hidden group-open:inline">Hide</span>
      </summary>
      <div className="px-6 pb-6 space-y-4 border-t border-slate-100 pt-4">
        <p className="text-sm text-slate-600">
          Upload a component question paper (PDF, DOCX, or TXT). The local AI detects questions,
          sub-parts (a/b/c), CO mappings, bonus items, and marks — then scales them to your chosen
          final weightage and downloads a single-component Excel template.
        </p>

        <div className="grid sm:grid-cols-2 gap-3">
          <label className="text-sm block">
            <span className="text-slate-600">Component name</span>
            <input
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              placeholder="e.g. MidSem, Quiz1, EndSem"
              value={componentName}
              onChange={(e) => setComponentName(e.target.value)}
            />
          </label>
          <label className="text-sm block">
            <span className="text-slate-600">Final weightage (%)</span>
            <input
              type="number"
              min={0.1}
              max={100}
              step={0.5}
              className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
              value={weightage}
              onChange={(e) => setWeightage(e.target.value)}
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            className="text-sm"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setAnalysis(null);
              setQuestions([]);
            }}
          />
          <button
            type="button"
            disabled={!file || busy}
            onClick={analyzePaper}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm disabled:opacity-50"
          >
            {busy ? "Analyzing…" : "Analyze paper"}
          </button>
        </div>

        {scaledPreview && (
          <p className="text-xs text-slate-500">
            Scale factor: {scaledPreview}× (paper total {analysis?.paper_total_marks} marks →{" "}
            {weightage}% weightage)
          </p>
        )}

        {error && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
        )}

        {analysis && questions.length > 0 && (
          <div className="space-y-3">
            <p className="text-sm font-medium text-slate-700">Confirm questions before download</p>
            <div className="overflow-x-auto border rounded-lg">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-600">
                  <tr>
                    <th className="py-2 px-2 text-left">Question</th>
                    <th className="py-2 px-2">CO</th>
                    <th className="py-2 px-2">Marks (paper)</th>
                    <th className="py-2 px-2">Bonus</th>
                  </tr>
                </thead>
                <tbody>
                  {questions.map((q) => (
                    <tr key={q.id} className="border-t border-slate-100">
                      <td className="py-1 px-2">
                        <input
                          className="w-full border rounded px-2 py-1"
                          value={q.label}
                          onChange={(e) => updateQuestion(q.id, { label: e.target.value })}
                        />
                      </td>
                      <td className="py-1 px-2">
                        <input
                          className="w-20 border rounded px-2 py-1"
                          value={q.co_label}
                          onChange={(e) => updateQuestion(q.id, { co_label: e.target.value })}
                        />
                      </td>
                      <td className="py-1 px-2">
                        <input
                          type="number"
                          min={0}
                          step={0.5}
                          className="w-20 border rounded px-2 py-1"
                          value={q.max_marks}
                          onChange={(e) =>
                            updateQuestion(q.id, { max_marks: Number(e.target.value) || 0 })
                          }
                        />
                      </td>
                      <td className="py-1 px-2 text-center">
                        <input
                          type="checkbox"
                          checked={q.is_bonus}
                          onChange={(e) => updateQuestion(q.id, { is_bonus: e.target.checked })}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button
              type="button"
              disabled={busy || !componentName.trim()}
              onClick={downloadTemplate}
              className="rounded-lg bg-teal-700 text-white px-4 py-2 text-sm disabled:opacity-50"
            >
              {busy ? "Generating…" : "Download component Excel"}
            </button>
          </div>
        )}
      </div>
    </details>
  );
}
