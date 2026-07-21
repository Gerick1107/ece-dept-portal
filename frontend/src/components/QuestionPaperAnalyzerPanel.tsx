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
  /** Raw CO text while editing — preserves trailing commas mid-type. */
  co_input: string;
  co_labels: string[];
  max_marks: number;
  is_bonus: boolean;
};

type AnalysisResult = {
  component_name: string;
  paper_total_marks: number;
  warnings?: string[];
  questions: Array<{
    label: string;
    co_label?: string;
    co_labels?: string[];
    max_marks: number;
    is_bonus: boolean;
  }>;
};

function parseCoLabels(q: AnalysisResult["questions"][number]): string[] {
  if (q.co_labels?.length) return q.co_labels;
  if (!q.co_label?.trim()) return [];
  return q.co_label
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

function formatCoInput(labels: string[]) {
  return labels.join(", ");
}

function parseCoInput(value: string): string[] {
  return value
    .split(",")
    .map((s) => s.trim().toUpperCase().replace(/\s+/g, ""))
    .filter(Boolean)
    .map((s) => (s.match(/^CO\d+$/i) ? s.replace(/^CO/i, "CO") : s));
}

function emptyQuestion(): AnalyzedQuestion {
  return {
    id: generateId(),
    label: `Q${Date.now() % 1000}`,
    co_input: "",
    co_labels: [],
    max_marks: 0,
    is_bonus: false,
  };
}

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
      if (!res.ok) {
        const detail = data.detail;
        const message =
          typeof detail === "string"
            ? detail
            : Array.isArray(detail)
              ? detail.map((d: { msg?: string }) => d?.msg).filter(Boolean).join("; ") || "Analysis failed"
              : "Analysis failed";
        throw new Error(message);
      }
      const result = data as AnalysisResult;
      setAnalysis(result);
      if (!componentName.trim() && result.component_name) {
        setComponentName(result.component_name);
      }
      setQuestions(
        result.questions.map((q) => {
          const co_labels = parseCoLabels(q);
          return {
            id: generateId(),
            label: q.label,
            co_input: formatCoInput(co_labels),
            co_labels,
            max_marks: Number(q.max_marks) || 0,
            is_bonus: q.is_bonus,
          };
        })
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
          questions: questions.map(({ label, co_input, max_marks, is_bonus }) => {
            const co_labels = parseCoInput(co_input);
            return {
              label,
              co_labels,
              co_label: co_labels.join(", "),
              max_marks,
              is_bonus,
            };
          }),
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

  function deleteQuestion(id: string) {
    setQuestions((prev) => prev.filter((q) => q.id !== id));
  }

  function insertQuestionAfter(index: number) {
    setQuestions((prev) => {
      const next = [...prev];
      next.splice(index + 1, 0, emptyQuestion());
      return next;
    });
  }

  function appendQuestion() {
    setQuestions((prev) => [...prev, emptyQuestion()]);
  }

  const scaledPreview =
    analysis && Number(weightage) > 0 && analysis.paper_total_marks > 0
      ? (Number(weightage) / analysis.paper_total_marks).toFixed(3)
      : null;
  const questionsMissingCos = questions.filter(
    (q) => !q.is_bonus && parseCoInput(q.co_input).length === 0
  );

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

        {analysis && (
          <div className="space-y-3">
            {questionsMissingCos.length > 0 && (
              <div
                role="alert"
                className="text-sm text-amber-900 bg-amber-50 border border-amber-300 rounded px-3 py-2"
              >
                <span className="font-medium">No COs found</span> for{" "}
                {questionsMissingCos.map((q) => q.label).join(", ")}. Manually edit/add the CO
                mappings before downloading.
              </div>
            )}
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium text-slate-700">
                {questions.length > 0
                  ? "Confirm or fix questions before download"
                  : "No questions detected — add them manually"}
              </p>
              <button
                type="button"
                onClick={appendQuestion}
                className="text-xs rounded border border-slate-300 px-2 py-1 hover:bg-slate-50"
              >
                + Add question
              </button>
            </div>

            {questions.length > 0 && (
              <div className="overflow-x-auto border rounded-lg">
                <table className="w-full text-xs">
                  <thead className="bg-slate-50 text-slate-600">
                    <tr>
                      <th className="py-2 px-2 text-left">Question</th>
                      <th className="py-2 px-2 text-left">CO(s)</th>
                      <th className="py-2 px-2">Marks (paper)</th>
                      <th className="py-2 px-2">Bonus</th>
                      <th className="py-2 px-2 w-28">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {questions.map((q, index) => (
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
                            className={`w-full min-w-[6rem] border rounded px-2 py-1 ${
                              !q.is_bonus && parseCoInput(q.co_input).length === 0
                                ? "border-amber-500 bg-amber-50"
                                : ""
                            }`}
                            placeholder={q.is_bonus ? "Not required" : "Add CO1, CO2"}
                            value={q.co_input}
                            onChange={(e) =>
                              updateQuestion(q.id, {
                                co_input: e.target.value,
                                co_labels: parseCoInput(e.target.value),
                              })
                            }
                            disabled={q.is_bonus}
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
                        <td className="py-1 px-2">
                          <div className="flex flex-col gap-1">
                            <button
                              type="button"
                              onClick={() => insertQuestionAfter(index)}
                              className="text-teal-700 hover:underline text-left"
                            >
                              Insert below
                            </button>
                            <button
                              type="button"
                              onClick={() => deleteQuestion(q.id)}
                              className="text-red-600 hover:underline text-left"
                            >
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <button
              type="button"
              disabled={busy || !componentName.trim() || questions.length === 0}
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
