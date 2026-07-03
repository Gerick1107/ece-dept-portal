import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { createBudgetRecord, deleteBudgetRecord, downloadBudgetInvoice, listBudgetRecords, updateBudgetRecord, uploadBudgetInvoice } from "../budgetApi";

type IncomeRecord = {
  id: number;
  date?: string;
  financialYear?: string;
  budgetHead: string;
  amountText?: string;
  amount: number;
  description?: string;
  notes?: string;
  utilisedAmountLakh: number;
  purchasesFor?: string;
  invoice?: string;
  invoiceUrl?: string;
};

type FormState = {
  date: string;
  budgetHead: string;
  approvedAmount: string;
  utilizedAmount: string;
  description: string;
  purchasesFor: string;
  invoiceName: string;
  invoiceUrl: string;
};

const initialForm: FormState = {
  date: "",
  budgetHead: "",
  approvedAmount: "",
  utilizedAmount: "",
  description: "",
  purchasesFor: "",
  invoiceName: "",
  invoiceUrl: "",
};

const currency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const inrNumber = new Intl.NumberFormat("en-IN", {
  maximumFractionDigits: 2,
});

function parseDateValue(dateValue?: string) {
  if (!dateValue) return null;
  const ddmmyyyy = dateValue.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (ddmmyyyy) {
    return new Date(Number(ddmmyyyy[3]), Number(ddmmyyyy[2]) - 1, Number(ddmmyyyy[1]));
  }
  const date = new Date(dateValue);
  return Number.isNaN(date.getTime()) ? null : date;
}

function getFinancialYear(dateValue?: string) {
  const date = parseDateValue(dateValue);
  if (!date) return "";
  const year = date.getFullYear();
  const month = date.getMonth() + 1;
  const startYear = month >= 4 ? year : year - 1;
  return `${startYear}-${startYear + 1}`;
}

function getRecordFinancialYear(record: IncomeRecord) {
  return getFinancialYear(record.date) || record.financialYear || "2026-2027";
}

function getUtilizedAmount(record: IncomeRecord) {
  return Number(record.utilisedAmountLakh || 0) * 100000;
}

function matchesSearch(record: IncomeRecord, query: string) {
  const normalizedQuery = query.trim().toLowerCase();
  if (!normalizedQuery) return true;
  return Object.values(record).some((value) => String(value || "").toLowerCase().includes(normalizedQuery));
}

function exportCsv(fileName: string, rows: Record<string, unknown>[], columns: { label: string; value: string | ((row: Record<string, unknown>, index: number) => unknown) }[]) {
  const header = columns.map((column) => column.label);
  const body = rows.map((row, index) =>
    columns.map((column) => {
      const rawValue = typeof column.value === "function" ? column.value(row, index) : row[column.value];
      return `"${String(rawValue ?? "").replaceAll('"', '""')}"`;
    }),
  );
  const csv = [header, ...body].map((row) => row.join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export default function AccumulatedIncomePage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin" || user?.role === "hod";
  const [records, setRecords] = useState<IncomeRecord[]>([]);
  const [form, setForm] = useState<FormState>(initialForm);
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [headFilter, setHeadFilter] = useState("all");
  const [financialYearFilter, setFinancialYearFilter] = useState(() => getFinancialYear(new Date().toISOString()));
  const [expandedHeads, setExpandedHeads] = useState(() => new Set<string>());
  const [showHeadSuggestions, setShowHeadSuggestions] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const formSectionRef = useRef<HTMLElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    listBudgetRecords<IncomeRecord>("income")
      .then((items) => {
        if (!cancelled) setRecords(items);
      })
      .catch((loadError) => {
        if (!cancelled) setError(loadError instanceof Error ? loadError.message : "Could not load income records");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const budgetHeadOptions = useMemo(
    () => [...new Set(records.map((record) => record.budgetHead).filter(Boolean))],
    [records],
  );

  const matchingBudgetHeads = budgetHeadOptions.filter((head) =>
    head.toLowerCase().includes(form.budgetHead.trim().toLowerCase()),
  );

  const financialYearOptions = useMemo(
    () => [...new Set(records.map(getRecordFinancialYear))],
    [records],
  );

  const filteredRecords = useMemo(
    () =>
      records.filter((record) => {
        const matchesFinancialYear =
          financialYearFilter === "all" || getRecordFinancialYear(record) === financialYearFilter;
        const matchesHead = headFilter === "all" || record.budgetHead === headFilter;
        return matchesFinancialYear && matchesHead && matchesSearch(record, search);
      }),
    [financialYearFilter, headFilter, records, search],
  );

  const groupedBudgetHeads = useMemo(() => {
    const groups = new Map<
      string,
      {
        key: string;
        financialYear: string;
        head: string;
        approvedAmount: number;
        utilizedAmount: number;
        entries: IncomeRecord[];
      }
    >();

    filteredRecords.forEach((record) => {
      const financialYear = getRecordFinancialYear(record);
      const head = record.budgetHead || "Unassigned Budget Head";
      const key = `${financialYear}::${head}`;
      const group = groups.get(key) || {
        key,
        financialYear,
        head,
        approvedAmount: 0,
        utilizedAmount: 0,
        entries: [],
      };
      group.approvedAmount = Math.max(group.approvedAmount, Number(record.amount || 0));
      group.utilizedAmount += getUtilizedAmount(record);
      group.entries.push(record);
      groups.set(key, group);
    });

    return [...groups.values()].map((group) => ({
      ...group,
      remainingAmount: Math.max(group.approvedAmount - group.utilizedAmount, 0),
    }));
  }, [filteredRecords]);

  const totalBudget = groupedBudgetHeads.reduce((sum, group) => sum + group.approvedAmount, 0);
  const totalUtilized = groupedBudgetHeads.reduce((sum, group) => sum + group.utilizedAmount, 0);
  const totalRemaining = groupedBudgetHeads.reduce((sum, group) => sum + group.remainingAmount, 0);

  function findApprovedAmount(head: string, financialYear: string) {
    return records
      .filter((record) => record.budgetHead === head && getRecordFinancialYear(record) === financialYear)
      .reduce((maximum, record) => Math.max(maximum, Number(record.amount || 0)), 0);
  }

  const isExistingBudgetHead = records.some(
    (record) => record.budgetHead === form.budgetHead && getRecordFinancialYear(record) === getFinancialYear(form.date),
  );

  const otherUtilizedAmount = records
    .filter(
      (record) =>
        record.budgetHead === form.budgetHead &&
        getRecordFinancialYear(record) === getFinancialYear(form.date) &&
        (!editingId || Number(record.id) !== Number(editingId)),
    )
    .reduce((sum, record) => sum + getUtilizedAmount(record), 0);

  const calculatedTotalUtilized = otherUtilizedAmount + Number(form.utilizedAmount || 0);
  const calculatedRemainingAmount = Math.max(Number(form.approvedAmount || 0) - calculatedTotalUtilized, 0);

  function updateField(name: keyof FormState, value: string) {
    if (name === "budgetHead" || name === "date") {
      const nextHead = name === "budgetHead" ? value : form.budgetHead;
      const nextDate = name === "date" ? value : form.date;
      const approvedAmount = findApprovedAmount(nextHead, getFinancialYear(nextDate));
      setForm((current) => ({
        ...current,
        [name]: value,
        approvedAmount: approvedAmount ? String(approvedAmount) : name === "budgetHead" ? current.approvedAmount : "",
      }));
      return;
    }
    setForm((current) => ({ ...current, [name]: value }));
  }

  function selectBudgetHead(head: string) {
    const approvedAmount = findApprovedAmount(head, getFinancialYear(form.date));
    setForm((current) => ({
      ...current,
      budgetHead: head,
      approvedAmount: approvedAmount ? String(approvedAmount) : "",
    }));
    setShowHeadSuggestions(false);
  }

  function validateForm() {
    if (Number(form.approvedAmount) <= 0) throw new Error("Total approved amount must be greater than zero");
    if (Number(form.utilizedAmount) < 0) throw new Error("Utilized amount must be zero or greater");
    if (calculatedTotalUtilized > Number(form.approvedAmount || 0)) {
      throw new Error("Utilized amount cannot exceed the remaining budget");
    }
  }

  async function saveIncomeRecord(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setError("");
      setSuccess("");
      validateForm();

      const uploadedInvoice = invoiceFile ? await uploadBudgetInvoice(invoiceFile) : null;
      const payload: IncomeRecord = {
        id: editingId ?? Math.max(0, ...records.map((record) => record.id)) + 1,
        date: form.date,
        financialYear: getFinancialYear(form.date),
        budgetHead: form.budgetHead.trim(),
        amountText: `INR ${inrNumber.format(Number(form.approvedAmount))}`,
        amount: Number(form.approvedAmount),
        description: form.description.trim(),
        utilisedAmountLakh: Number(form.utilizedAmount || 0) / 100000,
        purchasesFor: form.purchasesFor.trim(),
        invoice: uploadedInvoice?.invoice || form.invoiceName.trim() || "Not Attached",
        invoiceUrl: uploadedInvoice?.invoiceUrl || form.invoiceUrl,
      };

      if (editingId) {
        const saved = await updateBudgetRecord<IncomeRecord>("income", editingId, payload);
        setRecords((current) => current.map((record) => (record.id === editingId ? saved : record)));
      } else {
        const saved = await createBudgetRecord<IncomeRecord>("income", payload);
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

  function editRecord(record: IncomeRecord) {
    setEditingId(record.id);
    setError("");
    setSuccess("");
    setForm({
      date: record.date || "",
      budgetHead: record.budgetHead || "",
      approvedAmount: String(record.amount || ""),
      utilizedAmount: String(getUtilizedAmount(record)),
      description: record.description || record.notes || "",
      purchasesFor: record.purchasesFor || "",
      invoiceName: record.invoice && record.invoice !== "Not attached" ? record.invoice : "",
      invoiceUrl: record.invoiceUrl || "",
    });
    setInvoiceFile(null);
    requestAnimationFrame(() => {
      formSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  async function deleteIncomeRecord(record: IncomeRecord) {
    const entriesUnderHead = records.filter(
      (item) => item.budgetHead === record.budgetHead && getRecordFinancialYear(item) === getRecordFinancialYear(record),
    ).length;
    const message =
      entriesUnderHead === 1
        ? `Warning: this is the only entry under "${record.budgetHead}" for ${getRecordFinancialYear(record)}. Deleting it will also remove the budget head. Continue?`
        : "Delete only this accumulated-income entry?";
    if (!window.confirm(message)) return;
    try {
      setError("");
      await deleteBudgetRecord("income", record.id);
      setRecords((current) => current.filter((item) => item.id !== record.id));
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "Delete failed");
    }
  }

  function toggleBudgetHead(key: string) {
    setExpandedHeads((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function exportRows() {
    const selectedFinancialYear = financialYearFilter === "all" ? "all-years" : financialYearFilter;
    exportCsv(`ece-accumulated-income-${selectedFinancialYear}.csv`, groupedBudgetHeads, [
      { label: "S. N.", value: (_group, index) => index + 1 },
      { label: "Budget Head", value: "head" },
      { label: "Total Amount Approved (INR)", value: (group) => inrNumber.format(Number(group.approvedAmount || 0)) },
      { label: "Utilized (INR)", value: (group) => inrNumber.format(Number(group.utilizedAmount || 0)) },
      { label: "Remaining (INR)", value: (group) => inrNumber.format(Number(group.remainingAmount || 0)) },
      { label: "Entries", value: (group) => (Array.isArray(group.entries) ? group.entries.length : 0) },
    ]);
  }

  return (
    <main className="space-y-6">
      <section className="grid gap-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm lg:grid-cols-[1fr_320px]">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Accumulated Budget</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">Institute's Accumulated Income - ECE Department</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Maintain accumulated-income entries, purchase purposes, and invoice proof under each budget head.
          </p>
        </div>
        <div className="rounded-lg border border-teal-100 bg-teal-50 p-5">
          <span className="text-xs font-bold uppercase text-slate-500">
            Remaining Amount · {financialYearFilter === "all" ? "All Financial Years" : `FY ${financialYearFilter}`}
          </span>
          <strong className="mt-2 block text-2xl text-teal-900">{currency.format(totalRemaining)}</strong>
          <p className="mt-2 text-sm text-slate-600">
            Budget {currency.format(totalBudget)} | Utilized {currency.format(totalUtilized)}
          </p>
        </div>
      </section>

      {loading && <p className="text-sm font-medium text-slate-600">Loading budget records...</p>}

      {isAdmin && (
        <section ref={formSectionRef} className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <h3 className="text-lg font-semibold text-slate-950">{editingId ? "Edit Income Entry" : "Add Income Entry"}</h3>
            <p className="mt-1 text-sm text-slate-600">
              Search for an existing budget head or enter a new one. Existing approved amounts load automatically for the entry date's financial year.
            </p>
          </div>

          <form className="grid gap-4 md:grid-cols-2" onSubmit={saveIncomeRecord}>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Entry Date
              <input className="rounded-lg border border-slate-300 px-3 py-2" required type="date" value={form.date} onChange={(event) => updateField("date", event.target.value)} />
              {form.date && <span className="text-xs text-slate-500">Financial year: {getFinancialYear(form.date)}</span>}
            </label>
            <label className="relative grid gap-1 text-sm font-medium text-slate-700">
              Budget Head
              <input
                className="rounded-lg border border-slate-300 px-3 py-2"
                required
                disabled={!form.date}
                autoComplete="off"
                value={form.budgetHead}
                onChange={(event) => {
                  updateField("budgetHead", event.target.value);
                  setShowHeadSuggestions(true);
                }}
                onFocus={() => setShowHeadSuggestions(true)}
                onBlur={() => setShowHeadSuggestions(false)}
                placeholder={form.date ? "Search or enter a new budget head" : "Select entry date first"}
              />
              {showHeadSuggestions && matchingBudgetHeads.length > 0 && (
                <div className="absolute left-0 right-0 top-full z-20 mt-1 max-h-64 overflow-y-auto rounded-lg border border-slate-200 bg-white shadow-lg">
                  {matchingBudgetHeads.map((head) => (
                    <button
                      type="button"
                      key={head}
                      onMouseDown={(event) => event.preventDefault()}
                      onClick={() => selectBudgetHead(head)}
                      className="block w-full border-b border-slate-100 px-3 py-2 text-left text-sm hover:bg-teal-50"
                    >
                      {head}
                    </button>
                  ))}
                </div>
              )}
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Total Amount Approved (INR)
              <input
                className="rounded-lg border border-slate-300 px-3 py-2"
                required
                readOnly={isExistingBudgetHead}
                min="1"
                type={isExistingBudgetHead ? "text" : "number"}
                value={isExistingBudgetHead && form.approvedAmount ? inrNumber.format(Number(form.approvedAmount)) : form.approvedAmount}
                onChange={(event) => updateField("approvedAmount", event.target.value)}
              />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Total Utilized Amount (INR)
              <input className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2" readOnly value={form.budgetHead ? inrNumber.format(calculatedTotalUtilized) : ""} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              New Entry Amount (INR)
              <input className="rounded-lg border border-slate-300 px-3 py-2" required min="0" type="number" value={form.utilizedAmount} onChange={(event) => updateField("utilizedAmount", event.target.value)} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Remaining Amount (INR)
              <input className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2" readOnly value={form.approvedAmount ? inrNumber.format(calculatedRemainingAmount) : ""} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Purchases For
              <input className="rounded-lg border border-slate-300 px-3 py-2" value={form.purchasesFor} onChange={(event) => updateField("purchasesFor", event.target.value)} placeholder="Panel & Camera" />
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
                      if (file) updateField("invoiceName", file.name);
                    }}
                  />
                </label>
                <span className="text-sm font-semibold text-slate-400">{invoiceFile?.name || "No file selected"}</span>
              </div>
              {form.invoiceName && <span className="text-xs text-slate-500">Current: {form.invoiceName}</span>}
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700 md:col-span-2">
              Description
              <textarea className="min-h-24 rounded-lg border border-slate-300 px-3 py-2" required value={form.description} onChange={(event) => updateField("description", event.target.value)} />
            </label>
            <div className="flex flex-wrap gap-2 md:col-span-2">
              <button className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-600" type="submit">
                {editingId ? "Update Income Entry" : "Save Income Entry"}
              </button>
              {editingId && (
                <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" type="button" onClick={() => { setEditingId(null); setForm(initialForm); setInvoiceFile(null); }}>
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
            <h3 className="text-lg font-semibold text-slate-950">Accumulated Income Budget Heads</h3>
            <p className="mt-1 text-sm text-slate-600">
              Each budget head appears once per financial year. Click a head to view its entries.
            </p>
          </div>
          <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" type="button" onClick={exportRows}>
            Export CSV
          </button>
        </div>

        <div className="mb-5 grid gap-3 md:grid-cols-3">
          <label className="grid gap-1 text-sm font-medium text-slate-700">
            Search
            <input className="rounded-lg border border-slate-300 px-3 py-2" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search budget head, description, purchase..." />
          </label>
          <label className="grid gap-1 text-sm font-medium text-slate-700">
            Budget Head
            <select className="rounded-lg border border-slate-300 px-3 py-2" value={headFilter} onChange={(event) => setHeadFilter(event.target.value)}>
              <option value="all">All budget heads</option>
              {budgetHeadOptions.map((head) => (
                <option key={head} value={head}>{head}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-medium text-slate-700">
            Financial Year
            <select className="rounded-lg border border-slate-300 px-3 py-2" value={financialYearFilter} onChange={(event) => setFinancialYearFilter(event.target.value)}>
              <option value="all">All financial years</option>
              {financialYearOptions.map((year) => (
                <option key={year}>{year}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-[900px] w-full border-collapse text-sm">
            <thead className="bg-teal-50 text-left text-teal-950">
              <tr>
                <th className="border-b border-slate-200 px-4 py-3">S.<br />N.</th>
                <th className="border-b border-slate-200 px-4 py-3">Budget Head</th>
                <th className="border-b border-slate-200 px-4 py-3">Budget</th>
                <th className="border-b border-slate-200 px-4 py-3">Utilized</th>
                <th className="border-b border-slate-200 px-4 py-3">Remaining</th>
                <th className="border-b border-slate-200 px-4 py-3">Entries</th>
              </tr>
            </thead>
            <tbody>
              {groupedBudgetHeads.map((group, index) => {
                const isExpanded = expandedHeads.has(group.key);
                return (
                  <tr key={group.key} className="align-top">
                    <td className="border-b border-slate-100 px-4 py-3">{index + 1}</td>
                      <td className="border-b border-slate-100 px-4 py-3">
                        <button className="flex w-full items-start gap-2 text-left font-semibold text-teal-900" type="button" aria-expanded={isExpanded} onClick={() => toggleBudgetHead(group.key)}>
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
                              <th className="border-b px-3 py-2">Description</th>
                              <th className="border-b px-3 py-2">Purchases For</th>
                              <th className="border-b px-3 py-2">Amount</th>
                              <th className="border-b px-3 py-2">Invoice</th>
                              {isAdmin && <th className="border-b px-3 py-2">Actions</th>}
                            </tr>
                          </thead>
                          <tbody>
                            {group.entries.map((record) => (
                              <tr key={record.id}>
                                <td className="border-b px-3 py-2">{record.date || "Not recorded"}</td>
                                <td className="border-b px-3 py-2">{record.description || record.notes || "No description"}</td>
                                <td className="border-b px-3 py-2">{record.purchasesFor || "-"}</td>
                                <td className="border-b px-3 py-2">{inrNumber.format(getUtilizedAmount(record))}</td>
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
                                      <button className="rounded border px-2 py-1 font-semibold" type="button" onClick={() => deleteIncomeRecord(record)}>Delete</button>
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
                    <td className="border-b border-slate-100 px-4 py-3">{currency.format(group.approvedAmount)}</td>
                    <td className="border-b border-slate-100 px-4 py-3">{currency.format(group.utilizedAmount)}</td>
                    <td className="border-b border-slate-100 px-4 py-3">{currency.format(group.remainingAmount)}</td>
                    <td className="border-b border-slate-100 px-4 py-3">{group.entries.length}</td>
                  </tr>
                );
              })}
              {groupedBudgetHeads.length === 0 && (
                <tr>
                  <td className="px-4 py-4 text-slate-500" colSpan={6}>No budget heads found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
