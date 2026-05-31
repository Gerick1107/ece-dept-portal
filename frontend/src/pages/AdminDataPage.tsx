import { useCallback, useEffect, useState } from "react";
import {
  deleteProjectUpload,
  downloadProjectUpload,
  listProjectUploads,
} from "../modules/projects/services/projectsApi";
import type { ProjectUploadRow } from "../modules/projects/types/projects";
import { apiGet, apiPostForm } from "../services/api";

type Overview = {
  runs: Array<{
    public_id: string;
    user_id: number;
    course_title: string;
    evaluation_type: string;
    status: string;
    marks_upload_id: number | null;
    has_excel: boolean;
    created_at: string | null;
  }>;
  uploads: Array<{
    id: number;
    user_id: number;
    upload_type: string;
    course_title: string | null;
    original_filename: string;
    status: string;
    created_at: string | null;
  }>;
  archives: Array<{
    id: number;
    evaluation_run_id: number | null;
    evaluation_run_public_id?: string | null;
    archive_path: string;
    archive_metadata: Record<string, unknown> | null;
    created_at: string | null;
  }>;
};

export default function AdminDataPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [projectUploads, setProjectUploads] = useState<ProjectUploadRow[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [r, uploads] = await Promise.all([
        apiGet<Overview>("/copo/admin/data-overview"),
        listProjectUploads().catch(() => ({ project_uploads: [] })),
      ]);
      setData(r);
      setProjectUploads(uploads.project_uploads);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load data");
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function purgeAll() {
    if (!window.confirm("Delete ALL CO-PO uploads, runs, archives, and files? This cannot be undone.")) {
      return;
    }
    setBusy(true);
    setMessage("");
    try {
      const r = await apiPostForm<{ message: string }>("/copo/admin/purge-all", new FormData());
      setMessage(r.message);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Purge failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteRun(publicId: string) {
    if (
      !window.confirm(
        `Delete evaluation run ${publicId}? This removes the live result file and run record only. Marks uploads and archived copies are kept.`
      )
    ) {
      return;
    }
    setBusy(true);
    try {
      await apiPostForm(`/copo/admin/runs/${publicId}/delete`, new FormData());
      setMessage(`Deleted run ${publicId}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteUpload(id: number) {
    if (!window.confirm(`Delete upload #${id}?`)) return;
    setBusy(true);
    try {
      await apiPostForm(`/copo/admin/uploads/${id}/delete`, new FormData());
      setMessage(`Deleted upload #${id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function deleteArchive(id: number) {
    if (!window.confirm(`Delete archive #${id}?`)) return;
    setBusy(true);
    try {
      await apiPostForm(`/copo/admin/archives/${id}/delete`, new FormData());
      setMessage(`Deleted archive #${id}`);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  async function archiveRun(publicId: string) {
    setBusy(true);
    try {
      const r = await apiPostForm<{ archived: boolean; detail?: string }>(
        `/copo/admin/runs/${publicId}/archive`,
        new FormData()
      );
      setMessage(r.archived ? `Archived run ${publicId}` : r.detail || "Archive failed");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Archive failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap justify-between items-start gap-3">
        <div>
          <h2 className="text-xl font-semibold text-slate-900">Data &amp; archives</h2>
          <p className="text-sm text-slate-600 mt-1 max-w-2xl">
            Manage evaluation runs, marks uploads, and archived report copies. Archives are created
            when you click &quot;Archive&quot; on a run that still has a result Excel — a copy is saved
            under <code className="text-xs bg-slate-100 px-1 rounded">storage/archives/</code>, the
            live result in <code className="text-xs bg-slate-100 px-1 rounded">storage/results/</code>{" "}
            is removed, and the linked marks upload is cleared.
          </p>
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={purgeAll}
          className="rounded-lg border border-red-300 text-red-800 px-4 py-2 text-sm hover:bg-red-50 disabled:opacity-50"
        >
          Purge all CO-PO data
        </button>
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
      {message && (
        <p className="text-sm text-teal-900 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">
          {message}
        </p>
      )}

      {!data ? (
        <p className="text-slate-500">Loading…</p>
      ) : (
        <>
          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <h3 className="font-medium px-4 py-3 border-b bg-slate-50">Evaluation runs</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-500 border-b">
                  <tr>
                    <th className="px-4 py-2">Course</th>
                    <th className="px-4 py-2">Status</th>
                    <th className="px-4 py-2">User</th>
                    <th className="px-4 py-2">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {data.runs.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-4 text-slate-500">
                        No evaluation runs yet.
                      </td>
                    </tr>
                  )}
                  {data.runs.map((run) => (
                    <tr key={run.public_id} className="border-b last:border-0">
                      <td className="px-4 py-2">{run.course_title}</td>
                      <td className="px-4 py-2">{run.status}</td>
                      <td className="px-4 py-2">{run.user_id}</td>
                      <td className="px-4 py-2 flex flex-wrap gap-2">
                        {run.has_excel && (
                          <button
                            type="button"
                            className="text-teal-700 hover:underline text-xs"
                            disabled={busy}
                            onClick={() => archiveRun(run.public_id)}
                          >
                            Archive
                          </button>
                        )}
                        <button
                          type="button"
                          className="text-red-700 hover:underline text-xs"
                          disabled={busy}
                          onClick={() => deleteRun(run.public_id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <h3 className="font-medium px-4 py-3 border-b bg-slate-50">Marks uploads</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-500 border-b">
                  <tr>
                    <th className="px-4 py-2">ID</th>
                    <th className="px-4 py-2">Type</th>
                    <th className="px-4 py-2">Course / file</th>
                    <th className="px-4 py-2">Status</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {data.uploads.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-4 text-slate-500">
                        No upload rows.
                      </td>
                    </tr>
                  )}
                  {data.uploads.map((u) => (
                    <tr key={u.id} className="border-b last:border-0">
                      <td className="px-4 py-2">{u.id}</td>
                      <td className="px-4 py-2">{u.upload_type}</td>
                      <td className="px-4 py-2">
                        {u.course_title || "—"}
                        <span className="block text-xs text-slate-500">{u.original_filename}</span>
                      </td>
                      <td className="px-4 py-2">{u.status}</td>
                      <td className="px-4 py-2">
                        <button
                          type="button"
                          className="text-red-700 hover:underline text-xs"
                          disabled={busy}
                          onClick={() => deleteUpload(u.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <h3 className="font-medium px-4 py-3 border-b bg-slate-50">Result archives</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-500 border-b">
                  <tr>
                    <th className="px-4 py-2">ID</th>
                    <th className="px-4 py-2">Run</th>
                    <th className="px-4 py-2">Path</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {data.archives.length === 0 && (
                    <tr>
                      <td colSpan={4} className="px-4 py-4 text-slate-500">
                        No archives yet. Use &quot;Archive&quot; on a run with a saved Excel report.
                      </td>
                    </tr>
                  )}
                  {data.archives.map((a) => (
                    <tr key={a.id} className="border-b last:border-0">
                      <td className="px-4 py-2">{a.id}</td>
                      <td className="px-4 py-2">
                        {a.evaluation_run_id ?? a.evaluation_run_public_id ?? "—"}
                      </td>
                      <td className="px-4 py-2 text-xs font-mono">{a.archive_path}</td>
                      <td className="px-4 py-2">
                        <button
                          type="button"
                          className="text-red-700 hover:underline text-xs"
                          disabled={busy}
                          onClick={() => deleteArchive(a.id)}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <h3 className="font-medium px-4 py-3 border-b bg-slate-50">Project uploads (BTP / IP)</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-slate-500 border-b">
                  <tr>
                    <th className="px-4 py-2">ID</th>
                    <th className="px-4 py-2">Filename</th>
                    <th className="px-4 py-2">Records</th>
                    <th className="px-4 py-2">Uploaded</th>
                    <th className="px-4 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {projectUploads.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-4 text-slate-500">
                        No project import files yet.
                      </td>
                    </tr>
                  )}
                  {projectUploads.map((u) => (
                    <tr key={u.id} className="border-b last:border-0">
                      <td className="px-4 py-2">{u.id}</td>
                      <td className="px-4 py-2">{u.filename}</td>
                      <td className="px-4 py-2">{u.record_count}</td>
                      <td className="px-4 py-2 text-xs">{u.uploaded_at ?? "—"}</td>
                      <td className="px-4 py-2 space-x-2">
                        <button
                          type="button"
                          className="text-teal-700 hover:underline text-xs"
                          disabled={busy}
                          onClick={() => downloadProjectUpload(u.id).catch((e) => setError(String(e)))}
                        >
                          Download
                        </button>
                        <button
                          type="button"
                          className="text-red-700 hover:underline text-xs"
                          disabled={busy}
                          onClick={async () => {
                            if (!window.confirm("Delete this upload file record?")) return;
                            setBusy(true);
                            try {
                              await deleteProjectUpload(u.id);
                              await load();
                            } catch (e) {
                              setError(e instanceof Error ? e.message : "Delete failed");
                            } finally {
                              setBusy(false);
                            }
                          }}
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
