import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import CoWarningsBanner from "../../components/CoWarningsBanner";
import CopoFullResultsView from "../../components/CopoFullResultsView";
import { apiGet, apiPostForm, downloadCopoFile } from "../../services/api";

export default function CopoResultsPage() {
  const { publicId } = useParams<{ publicId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState("");
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!publicId) return;
    apiGet<{
      course_title: string;
      course_filename?: string;
      mapping_filename?: string;
      scope_summary?: string;
      unique_COs: string[];
      intermediate: Record<string, unknown>;
      co_warnings?: string[];
      download_token?: string;
      download_filename?: string;
    }>(`/copo/results/${publicId}`)
      .then(setData)
      .catch((e) => setError(e instanceof Error ? e.message : "Not found"));
  }, [publicId]);

  async function confirmDelete() {
    if (!publicId) return;
    setDeleting(true);
    try {
      const fd = new FormData();
      fd.append("delete_excel_report", "true");
      await apiPostForm(`/copo/runs/${publicId}/delete-data`, fd);
      navigate("/copo");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
      setShowDeleteConfirm(false);
    } finally {
      setDeleting(false);
    }
  }

  if (error && !data) return <p className="text-red-700">{error}</p>;
  if (!data) return <p className="text-slate-500">Loading…</p>;

  const intermediate = (data.intermediate as Record<string, unknown>) || {};
  const cos = (data.unique_COs as string[]) || [];
  const coWarnings =
    (data.co_warnings as string[] | undefined) ||
    (intermediate.co_warnings as string[] | undefined) ||
    [];
  const downloadToken = data.download_token as string | undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap justify-between items-center gap-3">
        <h2 className="text-xl font-semibold">{String(data.course_title)}</h2>
        <div className="flex flex-wrap gap-2">
          {downloadToken && (
            <button
              type="button"
              onClick={() =>
                downloadCopoFile(
                  downloadToken,
                  (data.download_filename as string) ||
                    `${String(data.course_title)}_CO_PO_Percentage_Results.xlsx`
                )
              }
              className="rounded bg-green-700 text-white px-4 py-2 text-sm"
            >
              Download Excel
            </button>
          )}
          <button
            type="button"
            onClick={() => setShowDeleteConfirm(true)}
            className="rounded border border-red-300 text-red-700 px-4 py-2 text-sm hover:bg-red-50"
          >
            Delete evaluation data
          </button>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 rounded px-3 py-2">{error}</p>
      )}

      <CoWarningsBanner warnings={coWarnings} />
      <CopoFullResultsView
        courseTitle={String(data.course_title)}
        courseFilename={data.course_filename as string | undefined}
        mappingFilename={data.mapping_filename as string | undefined}
        uniqueCos={cos}
        intermediate={intermediate}
        scopeSummary={data.scope_summary as string | undefined}
      />

      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="bg-white rounded-xl p-6 max-w-md w-full shadow-xl space-y-4">
            <h3 className="font-semibold text-lg">Delete evaluation data?</h3>
            <p className="text-sm text-slate-600">
              This removes uploaded marks files, the generated Excel report, archives, and this
              evaluation record from the server. Aggregated results in your browser will be lost.
              This cannot be undone.
            </p>
            <div className="flex gap-2 justify-end">
              <button
                type="button"
                className="rounded border px-4 py-2 text-sm"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded bg-red-700 text-white px-4 py-2 text-sm disabled:opacity-50"
                onClick={confirmDelete}
                disabled={deleting}
              >
                {deleting ? "Deleting…" : "Delete permanently"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
