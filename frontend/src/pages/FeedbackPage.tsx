import { FormEvent, useCallback, useEffect, useState } from "react";
import { useAuth } from "../modules/auth/AuthContext";
import { apiGet, apiPatchJson, apiPostJson } from "../services/api";

type FeedbackItem = {
  id: number;
  user_id: number;
  faculty_name?: string | null;
  faculty_email?: string | null;
  message: string;
  is_resolved: boolean;
  created_at: string | null;
  resolved_at: string | null;
};

function formatWhen(iso: string | null) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export default function FeedbackPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [ok, setOk] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const data = await apiGet<{ items: FeedbackItem[] }>("/feedback");
      setItems(data.items);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load feedback");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setOk("");
    try {
      await apiPostJson("/feedback", { message });
      setMessage("");
      setOk("Feedback sent. Admins (and HoD) have been notified by email when SMTP is enabled.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send feedback");
    } finally {
      setBusy(false);
    }
  }

  async function toggleResolved(item: FeedbackItem) {
    setError("");
    try {
      await apiPatchJson(`/feedback/${item.id}`, { is_resolved: !item.is_resolved });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h2 className="text-xl font-semibold">Feedback</h2>
        <p className="text-sm text-slate-600 mt-1">
          {isAdmin
            ? "Review faculty feedback, mark items resolved or unresolved."
            : "Send feedback or suggestions to the department admins. You can see whether each item has been resolved."}
        </p>
      </div>

      {ok && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{ok}</p>}
      {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      {!isAdmin && (
        <form onSubmit={onSubmit} className="bg-white border rounded-xl p-6 space-y-3">
          <h3 className="font-medium">Send feedback</h3>
          <textarea
            required
            minLength={3}
            className="w-full border rounded-lg px-3 py-2 text-sm min-h-[120px]"
            placeholder="Describe your feedback…"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button
            type="submit"
            disabled={busy}
            className="rounded bg-teal-700 text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
          >
            {busy ? "Sending…" : "Submit"}
          </button>
        </form>
      )}

      <section className="bg-white border rounded-xl overflow-hidden">
        <div className="px-4 py-3 border-b">
          <h3 className="font-medium">{isAdmin ? "All feedback" : "Your feedback"}</h3>
        </div>
        <ul className="divide-y">
          {items.map((item) => (
            <li key={item.id} className="px-4 py-3 space-y-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm text-slate-600">
                  {isAdmin && (
                    <span className="font-medium text-slate-800">
                      {item.faculty_name} ({item.faculty_email}) ·{" "}
                    </span>
                  )}
                  {formatWhen(item.created_at)}
                </div>
                <span
                  className={`text-xs px-2 py-0.5 rounded ${
                    item.is_resolved ? "bg-teal-50 text-teal-800" : "bg-amber-50 text-amber-900"
                  }`}
                >
                  {item.is_resolved ? "Resolved" : "Unresolved"}
                </span>
              </div>
              <p className="text-sm text-slate-800 whitespace-pre-wrap">{item.message}</p>
              {isAdmin && (
                <button type="button" className="text-xs text-teal-800 underline" onClick={() => toggleResolved(item)}>
                  Mark as {item.is_resolved ? "unresolved" : "resolved"}
                </button>
              )}
            </li>
          ))}
          {!items.length && <li className="px-4 py-8 text-center text-sm text-slate-500">No feedback yet.</li>}
        </ul>
      </section>
    </div>
  );
}
