import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { createBudgetRecord, deleteBudgetRecord, downloadBudgetInvoice, listBudgetRecords, updateBudgetRecord, uploadBudgetInvoice } from "../budgetApi";

type ExpenseRecord = {
  id: number;
  head: string;
  budgetLakh: number;
  expensesDescription?: string;
  utilizedLakh?: number;
  balanceLakh?: number;
  vendor: string;
  date: string;
  amount: number;
  invoice?: string;
  invoiceUrl?: string;
  status: "Pending" | "Approved" | "Rejected";
};

type ExpenseForm = {
  head: string;
  budgetLakh: string;
  utilizedAmount: string;
  vendor: string;
  date: string;
  status: "Pending" | "Approved" | "Rejected";
  invoiceName: string;
  invoiceUrl: string;
};

const expenditureBudgetHeads = [
  "Internal engagements (Refreshment and other related Expenses for department/Centre faculty Meetings, Seminars, official Lunch/ Dinners etc.)",
  "Expenditure on student & faculty recruitment",
  "Provision of support to students of department/centre for Presenting at conferences/events etc. including organizing events",
  "External engagement (Expenditure on Travel and stay of Experts/Visitors for a seminar or otherwise for Interaction and payment of honorarium, Gifts/Mementoes/Souvenirs to Guest/Speakers/faculty and for workshops/Seminars/Conferences etc.)",
  "Consumables & Non-consumables",
  "Industry Day/ECE Day",
  "Department publicity (alumni meet, hackathons/student club activities/ competitions/ IEEE advertisements/ professional videos etc.)",
  "Department development budget",
];

const initialForm: ExpenseForm = {
  head: "",
  budgetLakh: "",
  utilizedAmount: "",
  vendor: "ECE Department",
  date: "",
  status: "Pending",
  invoiceName: "",
  invoiceUrl: "",
};

const currency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const numberFormat = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

function getFinancialYear(dateValue?: string) {
  if (!dateValue) return "";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const startYear = date.getMonth() + 1 >= 4 ? year : year - 1;
  return `${startYear}-${startYear + 1}`;
}

function matchesSearch(record: ExpenseRecord, query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return Object.values(record).some((value) => String(value || "").toLowerCase().includes(normalized));
}

function exportCsv(fileName: string, rows: ExpenseRecord[]) {
  const columns = ["Date", "Budget Head", "Budget (Lakh)", "Utilized", "Remaining", "Vendor", "Status", "Invoice"];
  const body = rows.map((row) => [
    row.date,
    row.head,
    row.budgetLakh,
    row.amount,
    Math.max(row.budgetLakh * 100000 - row.amount, 0),
    row.vendor,
    row.status,
    row.invoice || "Not Attached",
  ]);
  const csv = [columns, ...body].map((line) => line.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export default function ExpenditureBudgetPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin" || user?.role === "hod";
  const [records, setRecords] = useState<ExpenseRecord[]>([]);
  const [form, setForm] = useState<ExpenseForm>(initialForm);
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [headFilter, setHeadFilter] = useState("all");
  const [financialYearFilter, setFinancialYearFilter] = useState(() => getFinancialYear(new Date().toISOString()));
  const [expandedHeads, setExpandedHeads] = useState(() => new Set<string>());
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");
  const formRef = useRef<HTMLElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listBudgetRecords<ExpenseRecord>("expenses")
      .then((items) => {
        if (!cancelled) setRecords(items);
      })
      .catch((loadError) => {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : "Could not load expenditure records");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const budgetHeadOptions = useMemo(
    () => [...new Set([...expenditureBudgetHeads, ...records.map((record) => record.head).filter(Boolean)])],
    [records],
  );

  const filteredRecords = useMemo(
    () =>
      records.filter((record) => {
        const matchesHead = headFilter === "all" || record.head === headFilter;
        const matchesYear = financialYearFilter === "all" || getFinancialYear(record.date) === financialYearFilter;
        return matchesHead && matchesYear && matchesSearch(record, search);
      }),
    [financialYearFilter, headFilter, records, search],
  );

  const financialYearOptions = useMemo(
    () => [...new Set(records.map((record) => getFinancialYear(record.date)).filter(Boolean))],
    [records],
  );

  const groupedHeads = useMemo(() => {
    const groups = new Map<string, { head: string; budgetLakh: number; entries: ExpenseRecord[]; utilizedAmount: number; remainingAmount: number }>();
    filteredRecords.forEach((record) => {
      const group = groups.get(record.head) || {
        head: record.head,
        budgetLakh: 0,
        entries: [],
        utilizedAmount: 0,
        remainingAmount: 0,
      };
      group.budgetLakh = Math.max(group.budgetLakh, Number(record.budgetLakh || 0));
      group.entries.push(record);
      group.utilizedAmount += Number(record.amount || 0);
      group.remainingAmount = Math.max(group.budgetLakh * 100000 - group.utilizedAmount, 0);
      groups.set(record.head, group);
    });
    return [...groups.values()];
  }, [filteredRecords]);

  const totalBudget = groupedHeads.reduce((sum, group) => sum + group.budgetLakh * 100000, 0);
  const totalUtilized = groupedHeads.reduce((sum, group) => sum + group.utilizedAmount, 0);
  const totalRemaining = Math.max(totalBudget - totalUtilized, 0);
  const otherUtilizedForHead = records
    .filter((record) => record.head === form.head && (!editingId || record.id !== editingId))
    .reduce((sum, record) => sum + Number(record.amount || 0), 0);
  const calculatedRemaining = Math.max(Number(form.budgetLakh || 0) * 100000 - otherUtilizedForHead - Number(form.utilizedAmount || 0), 0);

  async function saveExpense(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setSuccess("");
      setError("");
      if (Number(form.budgetLakh) <= 0) throw new Error("Budget must be greater than zero");
      if (Number(form.utilizedAmount) < 0) throw new Error("Utilized amount must be zero or greater");
      if (calculatedRemaining < 0) throw new Error("Utilized amount cannot exceed the remaining budget");

      const amount = Number(form.utilizedAmount || 0);
      const uploadedInvoice = invoiceFile ? await uploadBudgetInvoice(invoiceFile) : null;
      const record: ExpenseRecord = {
        id: editingId ?? Math.max(0, ...records.map((item) => item.id)) + 1,
        head: form.head,
        budgetLakh: Number(form.budgetLakh),
        utilizedLakh: amount / 100000,
        balanceLakh: calculatedRemaining / 100000,
        vendor: form.vendor.trim(),
        date: form.date || "2026-04-01",
        amount,
        invoice: uploadedInvoice?.invoice || form.invoiceName.trim() || "Not Attached",
        invoiceUrl: uploadedInvoice?.invoiceUrl || form.invoiceUrl,
        status: form.status,
      };
      if (editingId) {
        const saved = await updateBudgetRecord<ExpenseRecord>("expenses", editingId, record);
        setRecords((current) => current.map((item) => (item.id === editingId ? saved : item)));
      } else {
        const saved = await createBudgetRecord<ExpenseRecord>("expenses", record);
        setRecords((current) => [saved, ...current]);
      }
      setEditingId(null);
      setForm(initialForm);
      setInvoiceFile(null);
      setSuccess("Saved Successfully");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Save failed");
    }
  }

  function editRecord(record: ExpenseRecord) {
    setEditingId(record.id);
    setSuccess("");
    setError("");
    setForm({
      head: record.head,
      budgetLakh: String(record.budgetLakh || ""),
      utilizedAmount: String(record.amount || 0),
      vendor: record.vendor || "ECE Department",
      date: record.date || "",
      status: record.status,
      invoiceName: record.invoice && record.invoice !== "Not attached" ? record.invoice : "",
      invoiceUrl: record.invoiceUrl || "",
    });
    setInvoiceFile(null);
    requestAnimationFrame(() => formRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  async function deleteRecord(record: ExpenseRecord) {
    if (!window.confirm(`Delete this ${currency.format(record.amount)} expenditure entry?`)) return;
    try {
      setError("");
      await deleteBudgetRecord("expenses", record.id);
      setRecords((current) => current.filter((item) => item.id !== record.id));
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Delete failed");
    }
  }

  function toggleHead(head: string) {
    setExpandedHeads((current) => {
      const next = new Set(current);
      if (next.has(head)) next.delete(head);
      else next.add(head);
      return next;
    });
  }

  return (
    <main className="space-y-6">
      <section className="grid gap-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm lg:grid-cols-[1fr_320px]">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Expenditure Budget</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">ECE Expenditure Budget</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Manage expenditure particulars, utilization, balance, status, vendors, and invoice references.
          </p>
        </div>
        <div className="rounded-lg border border-teal-100 bg-teal-50 p-5">
          <span className="text-xs font-bold uppercase text-slate-500">
            Remaining Amount · {financialYearFilter === "all" ? "All Financial Years" : `FY ${financialYearFilter}`}
          </span>
          <strong className="mt-2 block text-2xl text-teal-900">{currency.format(totalRemaining)}</strong>
          <p className="mt-2 text-sm text-slate-600">Budget {currency.format(totalBudget)} | Utilized {currency.format(totalUtilized)}</p>
        </div>
      </section>

      {loading && <p className="text-sm font-medium text-slate-600">Loading expenditure records...</p>}

      {isAdmin && (
        <section ref={formRef} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <h3 className="text-lg font-semibold text-slate-950">{editingId ? "Edit Expenditure Entry" : "Add Expenditure Entry"}</h3>
            <p className="mt-1 text-sm text-slate-600">Choose a budget head, enter its approved budget and utilization entry.</p>
          </div>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={saveExpense}>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Entry Date
              <input className="rounded-lg border border-slate-300 px-3 py-2" required type="date" value={form.date} onChange={(event) => setForm((current) => ({ ...current, date: event.target.value }))} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Budget Head
              <input className="rounded-lg border border-slate-300 px-3 py-2" required list="expenditure-heads" value={form.head} onChange={(event) => setForm((current) => ({ ...current, head: event.target.value }))} />
              <datalist id="expenditure-heads">
                {budgetHeadOptions.map((head) => <option key={head} value={head} />)}
              </datalist>
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Total Budget Approved (Lakh)
              <input className="rounded-lg border border-slate-300 px-3 py-2" required min="0.01" step="0.01" type="number" value={form.budgetLakh} onChange={(event) => setForm((current) => ({ ...current, budgetLakh: event.target.value }))} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              New Entry Amount (INR)
              <input className="rounded-lg border border-slate-300 px-3 py-2" required min="0" type="number" value={form.utilizedAmount} onChange={(event) => setForm((current) => ({ ...current, utilizedAmount: event.target.value }))} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Remaining Amount (INR)
              <input className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2" readOnly value={numberFormat.format(calculatedRemaining)} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Vendor
              <input className="rounded-lg border border-slate-300 px-3 py-2" value={form.vendor} onChange={(event) => setForm((current) => ({ ...current, vendor: event.target.value }))} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Status
              <select className="rounded-lg border border-slate-300 px-3 py-2" value={form.status} onChange={(event) => setForm((current) => ({ ...current, status: event.target.value as ExpenseForm["status"] }))}>
                <option>Pending</option>
                <option>Approved</option>
                <option>Rejected</option>
              </select>
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Invoice PDF
              <div className="flex flex-wrap items-center gap-3">
                <label className="inline-flex cursor-pointer items-center gap-2 rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-teal-600">
                  <svg aria-hidden="true" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                    <path d="M12 16V4m0 0 4 4m-4-4-4 4" strokeLinecap="round" strokeLinejoin="round" />
                    <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                  Choose file
                  <input
                    className="sr-only"
                    accept="application/pdf"
                    type="file"
                    onChange={(event) => {
                      const file = event.target.files?.[0] || null;
                      setInvoiceFile(file);
                      if (file) setForm((current) => ({ ...current, invoiceName: file.name }));
                    }}
                  />
                </label>
                <span className="text-sm font-semibold text-slate-400">{invoiceFile?.name || "No file selected"}</span>
              </div>
              {form.invoiceName && <span className="text-xs text-slate-500">Current: {form.invoiceName}</span>}
            </label>
            <div className="flex flex-wrap gap-2 md:col-span-2">
              <button className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-600" type="submit">
                {editingId ? "Update Expenditure Entry" : "Save Expenditure Entry"}
              </button>
              {editingId && (
                <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium" type="button" onClick={() => { setEditingId(null); setForm(initialForm); setInvoiceFile(null); }}>
                  Cancel Edit
                </button>
              )}
            </div>
            {success && <p className="text-sm font-semibold text-emerald-700 md:col-span-2">{success}</p>}
            {error && <p className="text-sm font-semibold text-red-700 md:col-span-2">{error}</p>}
          </form>
        </section>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-slate-950">Expenditure Budget Heads</h3>
            <p className="mt-1 text-sm text-slate-600">Click a budget head to view its expenditure entries.</p>
          </div>
          <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50" type="button" onClick={() => exportCsv("ece-expenditure-budget.csv", filteredRecords)}>
            Export CSV
          </button>
        </div>
        <div className="mb-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1fr)]">
          <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
            Search
            <input className="min-w-0 rounded-lg border border-slate-300 px-3 py-2" value={search} onChange={(event) => setSearch(event.target.value)} />
          </label>
          <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
            Budget Head
            <select className="min-w-0 max-w-full truncate rounded-lg border border-slate-300 px-3 py-2" value={headFilter} onChange={(event) => setHeadFilter(event.target.value)}>
              <option value="all">All budget heads</option>
              {budgetHeadOptions.map((head) => <option key={head} value={head}>{head}</option>)}
            </select>
          </label>
          <label className="grid min-w-0 gap-1 text-sm font-medium text-slate-700">
            Financial Year
            <select className="min-w-0 rounded-lg border border-slate-300 px-3 py-2" value={financialYearFilter} onChange={(event) => setFinancialYearFilter(event.target.value)}>
              <option value="all">All financial years</option>
              {financialYearOptions.map((year) => <option key={year}>{year}</option>)}
            </select>
          </label>
        </div>
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-[900px] w-full text-sm">
            <thead className="bg-teal-50 text-left text-teal-950">
              <tr>
                <th className="border-b border-slate-200 px-4 py-3">S. N.</th>
                <th className="border-b border-slate-200 px-4 py-3">Budget Head</th>
                <th className="border-b border-slate-200 px-4 py-3">Budget</th>
                <th className="border-b border-slate-200 px-4 py-3">Utilized</th>
                <th className="border-b border-slate-200 px-4 py-3">Remaining</th>
                <th className="border-b border-slate-200 px-4 py-3">Entries</th>
              </tr>
            </thead>
            <tbody>
              {groupedHeads.map((group, index) => {
                const isExpanded = expandedHeads.has(group.head);
                return (
                  <tr key={group.head} className="align-top">
                    <td className="border-b border-slate-100 px-4 py-3">{index + 1}</td>
                    <td className="border-b border-slate-100 px-4 py-3">
                      <button className="flex w-full items-start gap-2 text-left font-semibold text-teal-900" type="button" onClick={() => toggleHead(group.head)}>
                        <svg
                          aria-hidden="true"
                          className={`mt-1 h-3.5 w-3.5 shrink-0 transition-transform ${isExpanded ? "rotate-90" : ""}`}
                          fill="none"
                          stroke="currentColor"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth="2.5"
                          viewBox="0 0 24 24"
                        >
                          <path d="m9 18 6-6-6-6" />
                        </svg>
                        <span>{group.head}</span>
                      </button>
                      {isExpanded && (
                        <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
                          <table className="min-w-[760px] w-full text-xs">
                            <thead className="bg-slate-50 text-left">
                              <tr>
                                <th className="border-b px-3 py-2">Date</th>
                                <th className="border-b px-3 py-2">Vendor</th>
                                <th className="border-b px-3 py-2">Amount</th>
                                <th className="border-b px-3 py-2">Status</th>
                                <th className="border-b px-3 py-2">Invoice</th>
                                {isAdmin && <th className="border-b px-3 py-2">Actions</th>}
                              </tr>
                            </thead>
                            <tbody>
                              {group.entries.map((record) => (
                                <tr key={record.id}>
                                  <td className="border-b px-3 py-2">{record.date}</td>
                                  <td className="border-b px-3 py-2">{record.vendor}</td>
                                  <td className="border-b px-3 py-2">{currency.format(record.amount)}</td>
                                  <td className="border-b px-3 py-2">{record.status}</td>
                                  <td className="border-b px-3 py-2">
                                    {record.invoiceUrl ? (
                                      <button className="font-semibold text-teal-700 hover:underline" type="button" onClick={() => downloadBudgetInvoice(record.invoiceUrl || "", record.invoice || "invoice.pdf")}>
                                        {record.invoice || "View Invoice"}
                                      </button>
                                    ) : (
                                      record.invoice || "Not Attached"
                                    )}
                                  </td>
                                  {isAdmin && (
                                    <td className="border-b px-3 py-2">
                                      <div className="flex gap-2">
                                        <button className="rounded border px-2 py-1 font-semibold" type="button" onClick={() => editRecord(record)}>Edit</button>
                                        <button className="rounded border px-2 py-1 font-semibold" type="button" onClick={() => deleteRecord(record)}>Delete</button>
                                      </div>
                                    </td>
                                  )}
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </td>
                    <td className="border-b border-slate-100 px-4 py-3">{currency.format(group.budgetLakh * 100000)}</td>
                    <td className="border-b border-slate-100 px-4 py-3">{currency.format(group.utilizedAmount)}</td>
                    <td className="border-b border-slate-100 px-4 py-3">{currency.format(group.remainingAmount)}</td>
                    <td className="border-b border-slate-100 px-4 py-3">{group.entries.length}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
