import DocumentsPage from "./DocumentsPage";

export default function AllMeetingsPage() {
  return (
    <DocumentsPage
      documentType="all-meetings"
      title="All Meetings"
      description="Browse every meeting document across Senate, AAC, PGC, UGC, and ECE Faculty — filter by year and ask questions across the full archive."
      showDocumentType
      disableUpload
    />
  );
}
