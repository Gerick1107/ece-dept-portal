export default function PublicationsModuleIntro() {
  return (
    <div className="bg-teal-50 border border-teal-200 rounded-xl p-4 text-sm text-teal-900">
      Publications data is scraped asynchronously and stored in MySQL.
      Frontend views read from cached database records only.
    </div>
  );
}
