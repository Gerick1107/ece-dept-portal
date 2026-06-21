import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import FileUploadField from "../../../components/FileUploadField";
import { apiDelete, apiGet, apiPostJson } from "../../../services/api";

type DocumentItem = {
  id: number;
  title: string;
  meeting_date: string | null;
  description: string | null;
  file_name: string;
  year: number;
};

type YearGroup = { year: number; documents: DocumentItem[] };

type QuerySource = {
  document_id: number;
  title: string;
  year: number;
  pages: number[];
};

type QueryChunk = {
  document_id: number;
  title: string;
  year: number;
  page_number: number | null;
  section_label: string | null;
  text: string;
};

type QueryResponse = {
  answer: string;
  sources: QuerySource[];
  context_chunks: QueryChunk[];
  not_found: boolean;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

function authHeaders(extra: Record<string, string> = {}) {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}`, ...extra } : extra;
}

export default function DocumentsPage({
  documentType,
  title,
  description,
}: {
  documentType: "senate" | "ece-faculty-meets";
  title: string;
  description: string;
}) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [years, setYears] = useState<YearGroup[]>([]);
  const [activeYear, setActiveYear] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [question, setQuestion] = useState("");
  const [queryBusy, setQueryBusy] = useState(false);
  const [queryError, setQueryError] = useState("");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [showContext, setShowContext] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadYear, setUploadYear] = useState(String(new Date().getFullYear()));
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const data = await apiGet<{ years: YearGroup[] }>(`/documents/${documentType}`);
      setYears(data.years);
      if (!activeYear && data.years.length) {
        setActiveYear(data.years[0].year);
      } else if (activeYear && !data.years.some((y) => y.year === activeYear)) {
        setActiveYear(data.years[0]?.year ?? null);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
    }
  }, [documentType, activeYear]);

  useEffect(() => {
    load();
  }, [load]);

  const activeDocs = years.find((y) => y.year === activeYear)?.documents ?? [];

  async function runQuery() {
    if (!question.trim()) return;
    setQueryBusy(true);
    setQueryError("");
    try {
      const result = await apiPostJson<QueryResponse>(`/documents/${documentType}/query`, { question: question.trim() });
      setQueryResult(result);
      setShowContext(false);
    } catch (e) {
      setQueryError(e instanceof Error ? e.message : "Query failed");
    } finally {
      setQueryBusy(false);
    }
  }

  function openViewer(docId: number) {
    setViewerUrl(`${API_BASE}/documents/${documentType}/${docId}/download`);
  }

  async function saveUpload() {
    if (!uploadFile) return;
    setUploadBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("file", uploadFile);
      form.append("year", uploadYear);
      const res = await fetch(`${API_BASE}/documents/${documentType}/upload`, {
        method: "POST",
        headers: authHeaders(),
        body: form,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error((err as { detail?: string }).detail ?? "Upload failed");
      }
      setShowUpload(false);
      setUploadFile(null);
      setMessage("Document uploaded and indexed.");
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploadBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{title}</h2>
          <p className="text-sm text-slate-600 mt-1">{description}</p>
        </div>
        {isAdmin && (
          <button type="button" onClick={() => setShowUpload(true)} className="rounded-lg bg-teal-700 text-white px-3 py-2 text-sm">
            Upload Document
          </button>
        )}
      </div>

      {message && <p className="text-sm text-teal-800 bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">{message}</p>}
      {error && <p className="text-sm text-red-800 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</p>}

      <div className="grid lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 space-y-4">
          <div className="flex flex-wrap gap-2">
            {years.map((group) => (
              <button
                key={group.year}
                type="button"
                onClick={() => setActiveYear(group.year)}
                className={`px-3 py-1.5 rounded-lg text-sm border ${
                  activeYear === group.year ? "bg-teal-700 text-white border-teal-700" : "bg-white border-slate-300"
                }`}
              >
                {group.year}
              </button>
            ))}
            {!years.length && <p className="text-sm text-slate-500">No documents uploaded yet.</p>}
          </div>

          <div className="bg-white border border-slate-200 rounded-xl shadow-sm divide-y">
            {activeDocs.map((doc) => (
              <div key={doc.id} className="p-4 space-y-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="font-medium text-slate-800">{doc.title}</h3>
                    <p className="text-xs text-slate-500">{doc.meeting_date || "Date not recorded"}</p>
                  </div>
                  <div className="flex gap-2">
                    <button type="button" className="text-xs px-2 py-1 rounded border" onClick={() => openViewer(doc.id)}>View</button>
                    <a
                      className="text-xs px-2 py-1 rounded border"
                      href={`${API_BASE}/documents/${documentType}/${doc.id}/download`}
                      download={doc.file_name}
                    >
                      Download
                    </a>
                    {isAdmin && (
                      <button
                        type="button"
                        className="text-xs px-2 py-1 rounded bg-red-50 text-red-700"
                        onClick={async () => {
                          if (!window.confirm("Delete this document?")) return;
                          await apiDelete(`/documents/${documentType}/${doc.id}`);
                          setMessage("Document deleted.");
                          await load();
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
                <p className="text-sm text-slate-600">{doc.description || "No description."}</p>
              </div>
            ))}
            {activeYear && !activeDocs.length && (
              <p className="p-6 text-center text-slate-500 text-sm">No documents for {activeYear} yet.</p>
            )}
          </div>
        </div>

        <section className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm space-y-3">
          <h3 className="font-semibold text-slate-800">Ask about this document set</h3>
          <textarea
            className="w-full border rounded-lg px-3 py-2 text-sm min-h-[90px]"
            placeholder="Ask a question about these minutes…"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
          />
          <button
            type="button"
            disabled={queryBusy || !question.trim()}
            onClick={runQuery}
            className="w-full rounded-lg bg-teal-700 text-white px-3 py-2 text-sm disabled:opacity-50"
          >
            {queryBusy ? "Searching…" : "Ask"}
          </button>
          {queryError && (
            <div className="text-sm text-red-800 space-y-2">
              <p>{queryError}</p>
              <button type="button" className="text-xs underline" onClick={runQuery}>Retry</button>
            </div>
          )}
          {queryResult && (
            <div className="space-y-3 text-sm">
              <p className="text-slate-800 whitespace-pre-wrap">{queryResult.answer}</p>
              {queryResult.sources.length > 0 && (
                <div>
                  <p className="font-medium text-slate-700">Sources</p>
                  <ul className="list-disc pl-5 text-slate-600">
                    {queryResult.sources.map((s) => (
                      <li key={s.document_id}>
                        {s.title} ({s.year})
                        {s.pages.length ? ` — pages ${s.pages.join(", ")}` : ""}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              <button type="button" className="text-xs text-teal-700 underline" onClick={() => setShowContext((v) => !v)}>
                {showContext ? "Hide context" : "Verify context"}
              </button>
              {showContext && (
                <div className="max-h-48 overflow-y-auto bg-slate-50 border rounded-lg p-2 text-xs text-slate-600 space-y-2">
                  {queryResult.context_chunks.map((chunk, index) => (
                    <div key={`${chunk.document_id}-${index}`}>
                      <p className="font-medium">{chunk.title} ({chunk.year}){chunk.page_number ? ` p.${chunk.page_number}` : ""}</p>
                      <p>{chunk.text}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </section>
      </div>

      {viewerUrl && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl w-full max-w-5xl h-[85vh] flex flex-col">
            <div className="flex justify-between items-center p-3 border-b">
              <span className="font-medium text-sm">PDF viewer</span>
              <button type="button" className="text-sm px-2 py-1 border rounded" onClick={() => setViewerUrl(null)}>Close</button>
            </div>
            <iframe title="PDF viewer" src={viewerUrl} className="flex-1 w-full" />
          </div>
        </div>
      )}

      {showUpload && isAdmin && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-md w-full p-6 space-y-4">
            <h3 className="font-semibold">Upload document</h3>
            <p className="text-sm text-slate-600">Title, date, and description are extracted from the PDF automatically.</p>
            <label className="text-sm block">
              <span className="text-slate-600 font-medium">Meeting year</span>
              <input
                type="number"
                className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
                value={uploadYear}
                onChange={(e) => setUploadYear(e.target.value)}
                placeholder="e.g. 2024"
              />
            </label>
            <FileUploadField
              label="PDF file"
              accept=".pdf,application/pdf"
              file={uploadFile}
              onFileChange={setUploadFile}
              hint="Senate or faculty meeting minutes (PDF only, max 25 MB)."
            />
            <div className="flex justify-end gap-2 pt-1">
              <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setShowUpload(false)}>Cancel</button>
              <button type="button" disabled={uploadBusy || !uploadFile} className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50" onClick={saveUpload}>
                {uploadBusy ? "Uploading…" : "Upload & index"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
