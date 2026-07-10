import { useCallback, useEffect, useState } from "react";
import {
  backfillCustomColumns,
  createCustomColumn,
  deleteCustomColumn,
  listCustomColumns,
  suggestCustomColumnSources,
  updateCustomColumn,
  type CustomColumn,
} from "../services/publicationsApi";

const CROSSREF_OPTIONS = ["", "issn", "isbn", "doi", "volume", "issue", "pages", "publisher", "container"];

export default function CustomColumnsPanel() {
  const [columns, setColumns] = useState<CustomColumn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const [label, setLabel] = useState("");
  const [description, setDescription] = useState("");
  const [sourceKeys, setSourceKeys] = useState("");
  const [crossrefField, setCrossrefField] = useState("");
  const [suggesting, setSuggesting] = useState(false);

  const refresh = useCallback(() => {
    setLoading(true);
    setError("");
    listCustomColumns()
      .then((cols) => setColumns(cols))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load custom columns"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleSuggest() {
    if (!label.trim()) {
      setError("Enter a column name first (e.g. ISSN).");
      return;
    }
    setSuggesting(true);
    setError("");
    setMessage("");
    try {
      const res = await suggestCustomColumnSources(label.trim(), description.trim() || undefined);
      if (res.source_keys) setSourceKeys(res.source_keys);
      if (res.crossref_field) setCrossrefField(res.crossref_field);
      setMessage(res.note || "Review the suggested sources, then save.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Suggestion failed");
    } finally {
      setSuggesting(false);
    }
  }

  async function handleCreate() {
    if (!label.trim()) {
      setError("Column name is required.");
      return;
    }
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await createCustomColumn({
        label: label.trim(),
        description: description.trim() || null,
        source_keys: sourceKeys.trim() || null,
        crossref_field: crossrefField || null,
      });
      setLabel("");
      setDescription("");
      setSourceKeys("");
      setCrossrefField("");
      setMessage("Column added. Use “Backfill custom columns” to fetch values for existing publications.");
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to add column");
    } finally {
      setBusy(false);
    }
  }

  async function handleToggle(col: CustomColumn) {
    try {
      await updateCustomColumn(col.id, { enabled: !col.enabled });
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to update column");
    }
  }

  async function handleDelete(col: CustomColumn) {
    if (!window.confirm(`Delete custom column “${col.label}”? Stored values remain in the database but stop being exported.`)) {
      return;
    }
    try {
      await deleteCustomColumn(col.id);
      refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete column");
    }
  }

  async function handleBackfill() {
    if (!window.confirm("Fetch missing custom-column values for all existing publications from publisher pages / Crossref? Runs in the background (no SerpAPI usage).")) {
      return;
    }
    setBusy(true);
    setMessage("");
    setError("");
    try {
      const res = await backfillCustomColumns();
      setMessage(res.message || "Custom-column backfill started.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Backfill failed to start");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="bg-white border rounded-xl p-5 space-y-4">
      <div>
        <h3 className="font-semibold">Custom Publication Columns</h3>
        <p className="text-sm text-slate-600 mt-1">
          Define extra columns that Google Scholar does not provide directly (e.g. ISSN). Values are
          fetched from the publisher link and Crossref during syncs and backfills, stored on each
          publication, and included in exports. Enter the publisher{" "}
          <code className="text-xs bg-slate-100 px-1 rounded">&lt;meta&gt;</code> tag name(s) to read,
          or let the local LLM suggest them for you to verify.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="text-sm">
          <span className="text-slate-600">Column name</span>
          <input
            className="mt-1 w-full border rounded-lg px-3 py-2"
            placeholder="e.g. ISSN"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-600">Description (optional)</span>
          <input
            className="mt-1 w-full border rounded-lg px-3 py-2"
            placeholder="What this column holds"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-600">Publisher meta tag name(s), comma-separated</span>
          <input
            className="mt-1 w-full border rounded-lg px-3 py-2"
            placeholder="e.g. citation_issn, prism.issn"
            value={sourceKeys}
            onChange={(e) => setSourceKeys(e.target.value)}
          />
        </label>
        <label className="text-sm">
          <span className="text-slate-600">Crossref fallback field (optional)</span>
          <select
            className="mt-1 w-full border rounded-lg px-3 py-2 bg-white"
            value={crossrefField}
            onChange={(e) => setCrossrefField(e.target.value)}
          >
            {CROSSREF_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt === "" ? "None" : opt}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleSuggest}
          disabled={suggesting || busy}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-60"
        >
          {suggesting ? "Asking LLM…" : "Suggest sources (LLM)"}
        </button>
        <button
          type="button"
          onClick={handleCreate}
          disabled={busy}
          className="rounded-lg bg-teal-700 text-white px-4 py-2 text-sm hover:bg-teal-800 disabled:opacity-60"
        >
          Add column
        </button>
        <button
          type="button"
          onClick={handleBackfill}
          disabled={busy || columns.length === 0}
          className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-60"
        >
          Backfill custom columns
        </button>
      </div>

      {message && (
        <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>
      )}
      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-slate-600 border-b">
            <tr>
              <th className="py-2 pr-3">Column</th>
              <th className="py-2 pr-3">Meta tags</th>
              <th className="py-2 pr-3">Crossref</th>
              <th className="py-2 pr-3">Enabled</th>
              <th className="py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="py-4 text-slate-500">
                  Loading…
                </td>
              </tr>
            ) : columns.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-4 text-slate-500">
                  No custom columns yet.
                </td>
              </tr>
            ) : (
              columns.map((col) => (
                <tr key={col.id} className="border-b border-slate-100">
                  <td className="py-2 pr-3">
                    <div className="font-medium">{col.label}</div>
                    {col.description && <div className="text-xs text-slate-500">{col.description}</div>}
                    <div className="text-xs text-slate-400">key: {col.key}</div>
                  </td>
                  <td className="py-2 pr-3 text-xs">{col.source_keys || "—"}</td>
                  <td className="py-2 pr-3 text-xs">{col.crossref_field || "—"}</td>
                  <td className="py-2 pr-3">
                    <button
                      type="button"
                      onClick={() => handleToggle(col)}
                      className={`text-xs px-2 py-1 rounded ${
                        col.enabled ? "bg-emerald-100 text-emerald-800" : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {col.enabled ? "Enabled" : "Disabled"}
                    </button>
                  </td>
                  <td className="py-2">
                    <button
                      type="button"
                      onClick={() => handleDelete(col)}
                      className="text-xs text-red-700 hover:underline"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
