import { useEffect, useState } from "react";
import { apiGet } from "../services/api";

type ComponentRow = {
  id: string;
  name: string;
  questions: number;
  bonus_question: boolean;
  is_bonus_component: boolean;
};

function newRow(preset?: string): ComponentRow {
  const isBonus = preset?.toLowerCase() === "bonus";
  return {
    id: crypto.randomUUID(),
    name: preset || "Quiz",
    questions: preset === "Project" ? 0 : 5,
    bonus_question: false,
    is_bonus_component: isBonus,
  };
}

async function downloadConstraintTemplate(
  courseCode: string,
  semester: string,
  components: ComponentRow[]
) {
  const token = localStorage.getItem("access_token");
  const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
  const res = await fetch(`${API_BASE}/copo/generate-constraint-template`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify({
      course_code: courseCode,
      semester,
      components: components.map((c) => ({
        name: c.name,
        questions: c.questions,
        bonus_question: c.bonus_question,
        is_bonus_component: c.is_bonus_component,
      })),
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    const detail = err.detail;
    throw new Error(typeof detail === "string" ? detail : "Could not generate template");
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = disposition.match(/filename="?([^";]+)"?/i);
  const filename = match?.[1] || `${courseCode}_${semester}_marks_template.xlsx`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function ConstraintMarksTemplatePanel({
  initialCourseCode = "",
  initialSemester = "",
}: {
  initialCourseCode?: string;
  initialSemester?: string;
}) {
  const [presets, setPresets] = useState<string[]>([]);
  const [courseCode, setCourseCode] = useState(initialCourseCode);
  const [semester, setSemester] = useState(initialSemester);
  const [components, setComponents] = useState<ComponentRow[]>([
    newRow("Quiz"),
    newRow("MidSem"),
    newRow("EndSem"),
  ]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setCourseCode((prev) => prev || initialCourseCode);
    setSemester((prev) => prev || initialSemester);
  }, [initialCourseCode, initialSemester]);

  useEffect(() => {
    apiGet<{ presets: string[] }>("/copo/template-components")
      .then((r) => setPresets(r.presets))
      .catch(() => setPresets(["Quiz", "MidSem", "EndSem", "Project", "Assignment", "Lab"]));
  }, []);

  function updateRow(id: string, patch: Partial<ComponentRow>) {
    setComponents((prev) => prev.map((r) => (r.id === id ? { ...r, ...patch } : r)));
  }

  function removeRow(id: string) {
    setComponents((prev) => (prev.length <= 1 ? prev : prev.filter((r) => r.id !== id)));
  }

  function addPreset(preset: string) {
    setComponents((prev) => [...prev, newRow(preset === "Custom" ? undefined : preset)]);
  }

  async function onGenerate() {
    setError("");
    if (!courseCode.trim() || !semester.trim()) {
      setError("Course code and semester are required.");
      return;
    }
    if (components.some((c) => !c.name.trim())) {
      setError("Every component row needs a name.");
      return;
    }
    setBusy(true);
    try {
      await downloadConstraintTemplate(courseCode.trim(), semester.trim(), components);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setBusy(false);
    }
  }

  const presetButtons = ["Quiz", "MidSem", "EndSem", "Project", "Assignment", "Lab", "Custom"];

  return (
    <details className="bg-white border border-slate-200 rounded-xl group">
      <summary className="cursor-pointer list-none px-6 py-4 font-medium text-slate-900 flex items-center justify-between gap-2">
        <span>Generate marks template (optional)</span>
        <span className="text-xs text-teal-700 font-medium group-open:hidden">Show</span>
        <span className="text-xs text-teal-700 font-medium hidden group-open:inline">Hide</span>
      </summary>
      <div className="px-6 pb-6 space-y-4 border-t border-slate-100 pt-4">
      <p className="text-sm text-slate-600">
        Configure assessments for this course and semester. Download a structured template (Branch,
        Roll No., merged component headers, CO / Max_Marks rows) to fill in and upload below.
        Multiple rows with the same name become Quiz1, Quiz2, etc. automatically.
      </p>

      <div className="grid sm:grid-cols-2 gap-3">
        <label className="text-sm block">
          <span className="text-slate-600">Course code</span>
          <input
            className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="e.g. ECE-113"
            value={courseCode}
            onChange={(e) => setCourseCode(e.target.value)}
          />
        </label>
        <label className="text-sm block">
          <span className="text-slate-600">Semester</span>
          <input
            className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
            placeholder="e.g. Summer 2026"
            value={semester}
            onChange={(e) => setSemester(e.target.value)}
          />
        </label>
      </div>

      <div className="space-y-2">
        <div className="flex flex-wrap gap-2 items-center justify-between">
          <span className="text-sm font-medium text-slate-700">Assessment components</span>
          <div className="flex flex-wrap gap-2">
            {presetButtons.map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => addPreset(p)}
                className={`text-xs rounded px-2 py-1 ${
                  p === "Custom"
                    ? "bg-teal-700 text-white"
                    : "border border-slate-300 hover:bg-slate-50"
                }`}
              >
                + {p}
              </button>
            ))}
          </div>
        </div>

        <div className="overflow-x-auto border rounded-lg">
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-600">
              <tr>
                <th className="py-2 px-2 text-left">Component name</th>
                <th className="py-2 px-2">Questions</th>
                <th className="py-2 px-2">Bonus Q</th>
                <th className="py-2 px-2">Bonus component</th>
                <th className="py-2 px-2" />
              </tr>
            </thead>
            <tbody>
              {components.map((row) => (
                <tr key={row.id} className="border-t border-slate-100">
                  <td className="py-1 px-2">
                    <input
                      list="component-presets"
                      className="w-full border rounded px-2 py-1 min-w-[120px]"
                      value={row.name}
                      onChange={(e) => updateRow(row.id, { name: e.target.value })}
                    />
                  </td>
                  <td className="py-1 px-2">
                    <input
                      type="number"
                      min={0}
                      max={50}
                      className="w-16 border rounded px-2 py-1"
                      title="0 = standalone (single column)"
                      value={row.questions}
                      disabled={row.is_bonus_component}
                      onChange={(e) =>
                        updateRow(row.id, {
                          questions: Number(e.target.value) || 0,
                          bonus_question:
                            Number(e.target.value) === 0 ? false : row.bonus_question,
                        })
                      }
                    />
                  </td>
                  <td className="py-1 px-2 text-center">
                    <input
                      type="checkbox"
                      checked={row.bonus_question}
                      disabled={row.is_bonus_component || row.questions === 0}
                      onChange={(e) => updateRow(row.id, { bonus_question: e.target.checked })}
                      title="Adds Bonus_Q{n+1} column inside this component"
                    />
                  </td>
                  <td className="py-1 px-2 text-center">
                    <input
                      type="checkbox"
                      checked={row.is_bonus_component}
                      onChange={(e) =>
                        updateRow(row.id, {
                          is_bonus_component: e.target.checked,
                          bonus_question: e.target.checked ? false : row.bonus_question,
                          questions: e.target.checked ? 0 : row.questions || 5,
                        })
                      }
                      title="Whole component is bonus (name gets _Bonus suffix)"
                    />
                  </td>
                  <td className="py-1 px-2">
                    <button
                      type="button"
                      onClick={() => removeRow(row.id)}
                      className="text-red-600 hover:underline"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <datalist id="component-presets">
            {presets.map((p) => (
              <option key={p} value={p} />
            ))}
          </datalist>
        </div>
        <p className="text-xs text-slate-500">
          Questions = 0 creates a standalone column (subheader “-”). Bonus Q adds an extra column after
          Q1…Qn. Bonus component marks the whole assessment as non-CO (e.g. Attendance_Bonus). Fill
          CO and Max_Marks in the downloaded file.
        </p>
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded px-3 py-2">
          {error}
        </p>
      )}

      <button
        type="button"
        onClick={onGenerate}
        disabled={busy}
        className="rounded-lg border border-teal-700 text-teal-800 px-4 py-2 text-sm font-medium hover:bg-teal-50 disabled:opacity-50"
      >
        {busy ? "Generating…" : "Download Constraint Excel"}
      </button>
      </div>
    </details>
  );
}
