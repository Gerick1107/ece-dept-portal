import { useCallback, useEffect, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import FileUploadField from "../../../components/FileUploadField";
import { apiDelete, apiGet, apiPostForm, apiPostJson } from "../../../services/api";

type MeetingFileRef = {
  id: number;
  file_name: string;
  description: string | null;
};

type DocumentItem = {
  id: number;
  title: string;
  meeting_date: string | null;
  year: number;
  has_agenda: boolean;
  has_minutes: boolean;
  agenda: MeetingFileRef | null;
  minutes: MeetingFileRef | null;
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
  file_role?: string;
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

type PreviewMeta = {
  title: string;
  meeting_date: string;
  description: string;
};

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";

const documentsListCache = new Map<string, YearGroup[]>();

function invalidateDocumentsListCache(documentType?: string) {
  if (documentType) documentsListCache.delete(documentType);
  else documentsListCache.clear();
}

function authHeaders(extra: Record<string, string> = {}) {
  const token = localStorage.getItem("access_token");
  return token ? { Authorization: `Bearer ${token}`, ...extra } : extra;
}

function formatMeetingDate(value: string | null): string {
  if (!value) return "Date not recorded";
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    const date = new Date(`${value}T00:00:00`);
    return date.toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  }
  return value;
}

async function fetchDocumentBlob(documentType: string, fileId: number): Promise<Blob> {
  const res = await fetch(`${API_BASE}/documents/${documentType}/files/${fileId}/download`, {
    headers: authHeaders(),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as { detail?: string }).detail ?? "Could not load PDF");
  }
  return res.blob();
}

export default function DocumentsPage({
  documentType,
  title,
  description,
}: {
  documentType: "senate" | "ece-faculty-meets" | "aac-meetings" | "ugc-meetings" | "pgc-meetings";
  title: string;
  description: string;
}) {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";

  const [years, setYears] = useState<YearGroup[]>(() => documentsListCache.get(documentType) ?? []);
  const [loading, setLoading] = useState(() => !documentsListCache.has(documentType));
  const [activeYear, setActiveYear] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [question, setQuestion] = useState("");
  const [queryBusy, setQueryBusy] = useState(false);
  const [queryError, setQueryError] = useState("");
  const [queryResult, setQueryResult] = useState<QueryResponse | null>(null);
  const [showContext, setShowContext] = useState(false);
  const [showUpload, setShowUpload] = useState(false);
  const [uploadStep, setUploadStep] = useState<"pick" | "review">("pick");
  const [uploadYear, setUploadYear] = useState(String(new Date().getFullYear()));
  const [uploadAgendaFile, setUploadAgendaFile] = useState<File | null>(null);
  const [uploadMinutesFile, setUploadMinutesFile] = useState<File | null>(null);
  const [agendaPreview, setAgendaPreview] = useState<PreviewMeta | null>(null);
  const [minutesPreview, setMinutesPreview] = useState<PreviewMeta | null>(null);
  const [previewBusy, setPreviewBusy] = useState(false);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [viewerUrl, setViewerUrl] = useState<string | null>(null);
  const [pdfBusyId, setPdfBusyId] = useState<number | null>(null);

  const load = useCallback(async (options?: { force?: boolean }) => {
    const cached = documentsListCache.get(documentType);
    if (cached && !options?.force) {
      setYears(cached);
      setLoading(false);
      setActiveYear((prev) => {
        if (prev && cached.some((y) => y.year === prev)) return prev;
        return cached[0]?.year ?? null;
      });
      return;
    }

    if (!cached) setLoading(true);
    setError("");
    try {
      const data = await apiGet<{ years: YearGroup[] }>(`/documents/${documentType}`);
      documentsListCache.set(documentType, data.years);
      setYears(data.years);
      setActiveYear((prev) => {
        if (prev && data.years.some((y) => y.year === prev)) return prev;
        return data.years[0]?.year ?? null;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, [documentType]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    return () => {
      if (viewerUrl) URL.revokeObjectURL(viewerUrl);
    };
  }, [viewerUrl]);

  const activeDocs = years.find((y) => y.year === activeYear)?.documents ?? [];

  function resetUploadModal() {
    setShowUpload(false);
    setUploadStep("pick");
    setUploadAgendaFile(null);
    setUploadMinutesFile(null);
    setAgendaPreview(null);
    setMinutesPreview(null);
    setPreviewBusy(false);
    setUploadBusy(false);
  }

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

  async function openViewer(docId: number) {
    setPdfBusyId(docId);
    setError("");
    try {
      const blob = await fetchDocumentBlob(documentType, docId);
      if (viewerUrl) URL.revokeObjectURL(viewerUrl);
      setViewerUrl(URL.createObjectURL(blob));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not open PDF");
    } finally {
      setPdfBusyId(null);
    }
  }

  async function downloadFile(file: MeetingFileRef) {
    setPdfBusyId(file.id);
    setError("");
    try {
      const blob = await fetchDocumentBlob(documentType, file.id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = file.file_name;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Download failed");
    } finally {
      setPdfBusyId(null);
    }
  }

  function closeViewer() {
    if (viewerUrl) URL.revokeObjectURL(viewerUrl);
    setViewerUrl(null);
  }

  async function previewFile(file: File): Promise<PreviewMeta> {
    const form = new FormData();
    form.append("file", file);
    const data = await apiPostForm<{ title: string; meeting_date: string | null; description: string }>(
      `/documents/${documentType}/upload/preview`,
      form
    );
    return {
      title: data.title,
      meeting_date: data.meeting_date ?? "",
      description: data.description,
    };
  }

  async function runPreview() {
    if (!uploadAgendaFile && !uploadMinutesFile) return;
    setPreviewBusy(true);
    setError("");
    try {
      if (uploadAgendaFile) setAgendaPreview(await previewFile(uploadAgendaFile));
      if (uploadMinutesFile) setMinutesPreview(await previewFile(uploadMinutesFile));
      setUploadStep("review");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not extract metadata");
    } finally {
      setPreviewBusy(false);
    }
  }

  async function saveUpload() {
    if (!uploadAgendaFile && !uploadMinutesFile) return;
    setUploadBusy(true);
    setError("");
    try {
      const form = new FormData();
      form.append("year", uploadYear);
      const title = minutesPreview?.title || agendaPreview?.title || "";
      const meetingDate = minutesPreview?.meeting_date || agendaPreview?.meeting_date || "";
      form.append("title", title);
      form.append("meeting_date", meetingDate);
      if (uploadAgendaFile) {
        form.append("agenda_file", uploadAgendaFile);
        form.append("agenda_description", agendaPreview?.description ?? "");
      }
      if (uploadMinutesFile) {
        form.append("minutes_file", uploadMinutesFile);
        form.append("minutes_description", minutesPreview?.description ?? "");
      }
      await apiPostForm(`/documents/${documentType}/upload`, form);
      invalidateDocumentsListCache(documentType);
      resetUploadModal();
      setMessage("Meeting uploaded and indexed.");
      await load({ force: true });
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
            {!years.length && loading && (
              <p className="text-sm text-slate-500">Loading documents…</p>
            )}
            {!years.length && !loading && (
              <p className="text-sm text-slate-500">No documents uploaded yet.</p>
            )}
          </div>

          <div className="bg-white border border-slate-200 rounded-xl shadow-sm divide-y">
            {loading && years.length > 0 && (
              <p className="p-4 text-sm text-slate-500">Refreshing…</p>
            )}
            {!loading && activeYear && !activeDocs.length && years.length > 0 && (
              <p className="p-6 text-center text-slate-500 text-sm">No documents for {activeYear} yet.</p>
            )}
            {activeDocs.map((doc) => (
              <div key={doc.id} className="p-4 space-y-2">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <h3 className="font-medium text-slate-800">{doc.title}</h3>
                    <p className="text-xs text-slate-500">{formatMeetingDate(doc.meeting_date)}</p>
                    <div className="flex gap-2 mt-1">
                      {!doc.has_agenda && <span className="text-xs bg-amber-50 text-amber-800 px-2 py-0.5 rounded">Missing Agenda</span>}
                      {!doc.has_minutes && <span className="text-xs bg-amber-50 text-amber-800 px-2 py-0.5 rounded">Missing Minutes</span>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {doc.agenda && (
                      <>
                        <button type="button" className="text-xs px-2 py-1 rounded border" disabled={pdfBusyId === doc.agenda.id} onClick={() => openViewer(doc.agenda!.id)}>View Agenda</button>
                        <button type="button" className="text-xs px-2 py-1 rounded border" disabled={pdfBusyId === doc.agenda.id} onClick={() => downloadFile(doc.agenda!)}>Download Agenda</button>
                      </>
                    )}
                    {doc.minutes && (
                      <>
                        <button type="button" className="text-xs px-2 py-1 rounded border" disabled={pdfBusyId === doc.minutes.id} onClick={() => openViewer(doc.minutes!.id)}>View Minutes</button>
                        <button type="button" className="text-xs px-2 py-1 rounded border" disabled={pdfBusyId === doc.minutes.id} onClick={() => downloadFile(doc.minutes!)}>Download Minutes</button>
                      </>
                    )}
                    {isAdmin && (
                      <button
                        type="button"
                        className="text-xs px-2 py-1 rounded bg-red-50 text-red-700"
                        onClick={async () => {
                          if (!window.confirm("Delete this meeting?")) return;
                          await apiDelete(`/documents/${documentType}/${doc.id}`);
                          invalidateDocumentsListCache(documentType);
                          setMessage("Meeting deleted.");
                          await load({ force: true });
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
                {(doc.agenda?.description || doc.minutes?.description) && (
                  <details className="text-sm text-slate-600">
                    <summary className="cursor-pointer text-teal-700 font-medium">Descriptions</summary>
                    {doc.agenda?.description && <p className="mt-2"><strong>Agenda:</strong> {doc.agenda.description}</p>}
                    {doc.minutes?.description && <p className="mt-2"><strong>Minutes:</strong> {doc.minutes.description}</p>}
                  </details>
                )}
              </div>
            ))}
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
                      <p className="font-medium">{chunk.title} ({chunk.year}){chunk.file_role ? ` — ${chunk.file_role}` : ""}{chunk.page_number ? ` p.${chunk.page_number}` : ""}</p>
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
              <button type="button" className="text-sm px-2 py-1 border rounded" onClick={closeViewer}>Close</button>
            </div>
            <iframe title="PDF viewer" src={viewerUrl} className="flex-1 w-full" />
          </div>
        </div>
      )}

      {showUpload && isAdmin && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-lg max-w-lg w-full p-6 space-y-4 max-h-[90vh] overflow-y-auto">
            <h3 className="font-semibold">Upload document</h3>

            {uploadStep === "pick" && (
              <>
                <p className="text-sm text-slate-600">
                  Choose the meeting year and at least one PDF (Agenda and/or Minutes).
                </p>
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
                  label="Agenda (PDF)"
                  accept=".pdf,application/pdf"
                  file={uploadAgendaFile}
                  onFileChange={setUploadAgendaFile}
                  hint="Optional if Minutes is provided."
                />
                <FileUploadField
                  label="Minutes (PDF)"
                  accept=".pdf,application/pdf"
                  file={uploadMinutesFile}
                  onFileChange={setUploadMinutesFile}
                  hint="Optional if Agenda is provided."
                />
                <div className="flex justify-end gap-2 pt-1">
                  <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={resetUploadModal}>Cancel</button>
                  <button
                    type="button"
                    disabled={previewBusy || (!uploadAgendaFile && !uploadMinutesFile)}
                    className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50"
                    onClick={runPreview}
                  >
                    {previewBusy ? "Extracting…" : "Extract & review"}
                  </button>
                </div>
              </>
            )}

            {uploadStep === "review" && (agendaPreview || minutesPreview) && (
              <>
                <p className="text-sm text-slate-600">Review extracted metadata before uploading.</p>
                {agendaPreview && (
                  <div className="space-y-2 border rounded-lg p-3">
                    <p className="text-sm font-medium">Agenda</p>
                    <input className="w-full border rounded-lg px-3 py-2 text-sm" value={agendaPreview.title} onChange={(e) => setAgendaPreview({ ...agendaPreview, title: e.target.value })} />
                    <textarea className="w-full border rounded-lg px-3 py-2 text-sm min-h-[80px]" value={agendaPreview.description} onChange={(e) => setAgendaPreview({ ...agendaPreview, description: e.target.value })} />
                  </div>
                )}
                {minutesPreview && (
                  <div className="space-y-2 border rounded-lg p-3">
                    <p className="text-sm font-medium">Minutes</p>
                    <input className="w-full border rounded-lg px-3 py-2 text-sm" value={minutesPreview.title} onChange={(e) => setMinutesPreview({ ...minutesPreview, title: e.target.value })} />
                    <textarea className="w-full border rounded-lg px-3 py-2 text-sm min-h-[80px]" value={minutesPreview.description} onChange={(e) => setMinutesPreview({ ...minutesPreview, description: e.target.value })} />
                  </div>
                )}
                <div className="flex justify-between gap-2 pt-1">
                  <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={() => setUploadStep("pick")}>Back</button>
                  <div className="flex gap-2">
                    <button type="button" className="px-3 py-2 text-sm border rounded-lg" onClick={resetUploadModal}>Cancel</button>
                    <button type="button" disabled={uploadBusy} className="px-3 py-2 text-sm bg-teal-700 text-white rounded-lg disabled:opacity-50" onClick={saveUpload}>
                      {uploadBusy ? "Uploading…" : "Confirm upload"}
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
