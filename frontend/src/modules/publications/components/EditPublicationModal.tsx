import { useEffect, useState } from "react";
import type { Publication, PublicationEditPayload } from "../types/publications";

type Props = {
  publication: Publication;
  onClose: () => void;
  onSave: (payload: PublicationEditPayload) => Promise<void>;
};

function Field({
  label,
  value,
  onChange,
  multiline = false,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
}) {
  return (
    <label className="block text-sm">
      <span className="text-slate-600">{label}</span>
      {multiline ? (
        <textarea
          className="mt-1 w-full border rounded-lg px-3 py-2 text-sm min-h-[72px]"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      ) : (
        <input
          className="mt-1 w-full border rounded-lg px-3 py-2 text-sm"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      )}
    </label>
  );
}

export default function EditPublicationModal({ publication, onClose, onSave }: Props) {
  const [publisher, setPublisher] = useState(publication.publisher || "");
  const [publicationDate, setPublicationDate] = useState(publication.publication_date || "");
  const [pages, setPages] = useState(publication.pages || "");
  const [journal, setJournal] = useState(publication.journal || "");
  const [conference, setConference] = useState(publication.conference || "");
  const [book, setBook] = useState(publication.book || "");
  const [volume, setVolume] = useState(publication.volume || "");
  const [issue, setIssue] = useState(publication.issue || "");
  const [patentOffice, setPatentOffice] = useState(publication.patent_office || "");
  const [patentNumber, setPatentNumber] = useState(publication.patent_number || "");
  const [applicationNumber, setApplicationNumber] = useState(publication.application_number || "");
  const [isManualBook, setIsManualBook] = useState(Boolean(publication.is_manual_book));
  const [customFields, setCustomFields] = useState<Record<string, string>>(
    publication.custom_fields || {}
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    const payload: PublicationEditPayload = {
      publisher: publisher.trim() || null,
      publication_date: publicationDate.trim() || null,
      pages: pages.trim() || null,
      journal: journal.trim() || null,
      conference: conference.trim() || null,
      book: book.trim() || null,
      volume: volume.trim() || null,
      issue: issue.trim() || null,
      is_manual_book: isManualBook,
      custom_fields: customFields,
    };
    if (publication.is_patent) {
      payload.patent_office = patentOffice.trim() || null;
      payload.patent_number = patentNumber.trim() || null;
      payload.application_number = applicationNumber.trim() || null;
    }
    try {
      await onSave(payload);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save changes");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h3 className="text-lg font-semibold">Edit publication</h3>
              <p className="text-sm text-slate-600 mt-1 break-words">{publication.title}</p>
              <p className="text-xs text-slate-500 mt-1">
                Title, authors/inventors, year, and citation count stay fixed so future Scholar syncs
                can still match this record. Edited fields are protected from overwrite.
              </p>
            </div>
            <button type="button" onClick={onClose} className="text-slate-500 hover:text-slate-800">
              ✕
            </button>
          </div>

          {!publication.is_patent && (
            <label className="flex items-center gap-2 text-sm bg-teal-50 border border-teal-200 rounded-lg px-3 py-2">
              <input
                type="checkbox"
                checked={isManualBook}
                onChange={(e) => setIsManualBook(e.target.checked)}
              />
              <span>
                Assign to <strong>Books</strong> tab (still remains under All Publications)
              </span>
            </label>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Field label="Journal" value={journal} onChange={setJournal} multiline />
            <Field label="Conference" value={conference} onChange={setConference} multiline />
            <Field label="Book / Book chapter" value={book} onChange={setBook} multiline />
            <Field label="Publisher" value={publisher} onChange={setPublisher} />
            <Field label="Publication date" value={publicationDate} onChange={setPublicationDate} />
            <Field label="Volume" value={volume} onChange={setVolume} />
            <Field label="Issue" value={issue} onChange={setIssue} />
            <Field label="Pages" value={pages} onChange={setPages} />
            {publication.is_patent && (
              <>
                <Field label="Patent office" value={patentOffice} onChange={setPatentOffice} />
                <Field label="Patent number" value={patentNumber} onChange={setPatentNumber} />
                <Field
                  label="Application number"
                  value={applicationNumber}
                  onChange={setApplicationNumber}
                />
              </>
            )}
          </div>

          {Object.keys(customFields).length > 0 && (
            <div className="space-y-2">
              <p className="text-sm font-medium text-slate-700">Custom columns</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {Object.entries(customFields).map(([key, value]) => (
                  <Field
                    key={key}
                    label={key}
                    value={value}
                    onChange={(next) => setCustomFields((prev) => ({ ...prev, [key]: next }))}
                  />
                ))}
              </div>
            </div>
          )}

          {error && (
            <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg border px-4 py-2 text-sm hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="rounded-lg bg-teal-700 text-white px-4 py-2 text-sm hover:bg-teal-800 disabled:opacity-60"
            >
              {saving ? "Saving…" : "Save changes"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
