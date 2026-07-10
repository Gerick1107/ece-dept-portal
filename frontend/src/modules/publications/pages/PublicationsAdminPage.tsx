import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import CustomColumnsPanel from "../components/CustomColumnsPanel";
import PublicationsModuleIntro from "../components/PublicationsModuleIntro";
import {
  backfillPublicationDates,
  getScrapeLogs,
  syncAllPublications,
  type ScrapeLogEntry,
} from "../services/publicationsApi";

export default function PublicationsAdminPage() {
  const { user, loading: authLoading } = useAuth();
  const isAdmin = user?.role === "admin";
  const [logs, setLogs] = useState<ScrapeLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [logsError, setLogsError] = useState("");
  const [syncMessage, setSyncMessage] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [backfilling, setBackfilling] = useState(false);

  const refreshLogs = useCallback(() => {
    if (!isAdmin) return;
    setLoading(true);
    setLogsError("");
    getScrapeLogs({ page: 1, page_size: 50 })
      .then((r) => setLogs(r.items ?? []))
      .catch((e) => {
        setLogs([]);
        setLogsError(e instanceof Error ? e.message : "Failed to load scrape logs");
      })
      .finally(() => setLoading(false));
  }, [isAdmin]);

  useEffect(() => {
    if (authLoading) return;
    if (isAdmin) {
      refreshLogs();
    } else {
      setLoading(false);
      setLogs([]);
    }
  }, [authLoading, isAdmin, refreshLogs]);

  if (authLoading) {
    return <p className="text-sm text-slate-500">Loading…</p>;
  }

  if (!isAdmin) {
    return <p className="text-sm text-slate-600">Admin access required.</p>;
  }

  async function handleSyncAll() {
    if (
      !window.confirm(
        "Check all active faculty Google Scholar profiles for new publications and patents via SerpAPI. This may use many API searches. Continue?"
      )
    ) {
      return;
    }
    setSyncing(true);
    setSyncMessage("");
    try {
      const res = await syncAllPublications();
      setSyncMessage(res.message || "Sync started. Check Scrape Logs for progress.");
      window.setTimeout(() => refreshLogs(), 5000);
    } catch (e) {
      setSyncMessage(e instanceof Error ? e.message : "Sync failed to start");
    } finally {
      setSyncing(false);
    }
  }

  async function handleBackfillDates() {
    if (
      !window.confirm(
        "Fill in exact publication dates for publications that only have a year or year-month. This reads publisher pages and Crossref (no SerpAPI usage) and runs in the background. Continue?"
      )
    ) {
      return;
    }
    setBackfilling(true);
    setSyncMessage("");
    try {
      const res = await backfillPublicationDates();
      setSyncMessage(res.message || "Date backfill started.");
    } catch (e) {
      setSyncMessage(e instanceof Error ? e.message : "Backfill failed to start");
    } finally {
      setBackfilling(false);
    }
  }

  return (
    <div className="space-y-6">
      <PublicationsModuleIntro />
      <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="text-xl font-semibold">Publications Administration</h2>
        <p className="text-sm text-slate-600">
          Fetches new publications and patents from each active faculty Scholar profile, stores full
          metadata (including patents), and links them to faculty. Uses SerpAPI key rotation from{" "}
          <code className="text-xs bg-slate-100 px-1 rounded">SERP_API_KEYS</code> in backend .env.
          The sync also fills exact publication dates for new entries (via publisher pages/Crossref,
          no SerpAPI cost).
        </p>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={handleSyncAll}
            disabled={syncing || backfilling}
            className="rounded-lg bg-teal-700 text-white px-4 py-2 text-sm hover:bg-teal-800 disabled:opacity-60"
          >
            {syncing ? "Starting…" : "Sync All Publications"}
          </button>
          <button
            type="button"
            onClick={handleBackfillDates}
            disabled={syncing || backfilling}
            className="rounded-lg border border-slate-300 px-4 py-2 text-sm hover:bg-slate-50 disabled:opacity-60"
          >
            {backfilling ? "Starting…" : "Backfill Missing Dates"}
          </button>
        </div>
        {syncMessage && (
          <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">
            {syncMessage}
          </p>
        )}
      </section>
      <CustomColumnsPanel />
      <section className="bg-white border rounded-xl p-5 space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Scrape Logs</h3>
          <button
            type="button"
            onClick={refreshLogs}
            className="text-sm text-teal-700 hover:underline"
          >
            Refresh
          </button>
        </div>
        {logsError && (
          <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
            {logsError}
            <span className="block mt-1 text-xs text-red-600">
              Ensure the backend is running (default proxy: port 8001) and you are logged in as
              admin.
            </span>
          </p>
        )}
        {loading ? (
          <p className="text-sm text-slate-500">Loading logs…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-left text-slate-600 border-b">
                <tr>
                  <th className="py-2 pr-3">Faculty</th>
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">New pubs</th>
                  <th className="py-2 pr-3">Started</th>
                  <th className="py-2 pr-3">Completed</th>
                  <th className="py-2">Errors</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-b border-slate-100">
                    <td className="py-2 pr-3">{log.faculty_name || `#${log.faculty_id}`}</td>
                    <td className="py-2 pr-3 capitalize">{log.status}</td>
                    <td className="py-2 pr-3">{log.new_publications_added}</td>
                    <td className="py-2 pr-3 text-xs">{formatDt(log.started_at)}</td>
                    <td className="py-2 pr-3 text-xs">{formatDt(log.completed_at)}</td>
                    <td
                      className="py-2 text-xs text-red-700 max-w-xs truncate"
                      title={log.errors || undefined}
                    >
                      {log.errors || "—"}
                    </td>
                  </tr>
                ))}
                {logs.length === 0 && !logsError && (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-slate-500">
                      No scrape logs yet. Run Sync All Publications to create entries.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function formatDt(value: string | null | undefined) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
