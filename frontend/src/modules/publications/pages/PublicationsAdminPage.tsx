import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import PublicationsModuleIntro from "../components/PublicationsModuleIntro";
import {
  getScrapeLogs,
  syncAllPublications,
  type ScrapeLogEntry,
} from "../services/publicationsApi";

export default function PublicationsAdminPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const [logs, setLogs] = useState<ScrapeLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncMessage, setSyncMessage] = useState("");
  const [syncing, setSyncing] = useState(false);

  const refreshLogs = useCallback(() => {
    setLoading(true);
    getScrapeLogs({ page_size: 50 })
      .then((r) => setLogs(r.items))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (isAdmin) refreshLogs();
  }, [isAdmin, refreshLogs]);

  if (!isAdmin) {
    return <p className="text-sm text-slate-600">Admin access required.</p>;
  }

  async function handleSyncAll() {
    if (!window.confirm("Check all faculty for new publications via SerpAPI. Continue?")) return;
    setSyncing(true);
    try {
      await syncAllPublications();
      setSyncMessage("Sync started. Check Scrape Logs for progress.");
      setTimeout(() => refreshLogs(), 3000);
    } catch (e) {
      setSyncMessage(e instanceof Error ? e.message : "Sync failed to start");
    } finally {
      setSyncing(false);
    }
  }

  return (
    <div className="space-y-6">
      <PublicationsModuleIntro />
      <section className="bg-white border rounded-xl p-5 space-y-4">
        <h2 className="text-xl font-semibold">Publications Administration</h2>
        <button
          type="button"
          onClick={handleSyncAll}
          disabled={syncing}
          className="rounded-lg bg-teal-700 text-white px-4 py-2 text-sm hover:bg-teal-800 disabled:opacity-60"
        >
          {syncing ? "Starting…" : "Sync All Publications"}
        </button>
        {syncMessage && (
          <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">
            {syncMessage}
          </p>
        )}
      </section>
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
                    <td className="py-2 text-xs text-red-700 max-w-xs truncate" title={log.errors || undefined}>
                      {log.errors || "—"}
                    </td>
                  </tr>
                ))}
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
