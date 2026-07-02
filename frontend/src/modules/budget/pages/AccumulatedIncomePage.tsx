import { Fragment, useMemo, useRef, useState } from "react";
import { useAuth } from "../../auth/AuthContext";

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
};

const seedRecords: IncomeRecord[] = [
  {
    id: 1,
    budgetHead: "End-to-End Testbed on Beyond 5G",
    amountText: "Rs. 50 Lakhs",
    amount: 5000000,
    description: "Hardware for Beyond 5G, including NTN, SDRs, UAVs, and underwater communication setups.",
    utilisedAmountLakh: 5.07933,
    purchasesFor: "",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 2,
    budgetHead: "Dedicated Servers for ECE Department",
    amountText: "Rs. 5 Crores",
    amount: 50000000,
    description: "DGX-like and CPU servers for high computational power needs in research.",
    utilisedAmountLakh: 0.59205,
    purchasesFor: "3.8 Cr, (Dr. Saket)",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 3,
    budgetHead: "Distinguished Guests",
    amountText: "Rs. 10 Lakhs/year for 2 years (Total 20 lakhs)",
    amount: 2000000,
    description: "Engage international faculty for mentoring and collaborative grant writing.",
    utilisedAmountLakh: 0,
    purchasesFor: "",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 4,
    budgetHead: "ECE Floor Transformation",
    amountText: "Rs. 3 Lakhs",
    amount: 300000,
    description: "Enhance floor with lab pictures, screens, and video demos.",
    utilisedAmountLakh: 0,
    purchasesFor: "",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 5,
    budgetHead: "Hosting Conferences",
    amountText: "Rs. 2 Lakhs/year for 2 years (Total 4 lakhs)",
    amount: 400000,
    description: "Hosting academic conferences to improve research visibility.",
    utilisedAmountLakh: 0,
    purchasesFor: "",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 6,
    budgetHead: "Scholarship for Top Performers",
    amountText: "Rs. 12 Lakhs for 2 years",
    amount: 1200000,
    description: "Retain high-performing students through scholarships.",
    utilisedAmountLakh: 1.51612,
    purchasesFor: "",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 7,
    budgetHead: "Inviting School Students",
    amountText: "Rs. 2.5 Lakhs for 2 years",
    amount: 250000,
    description: "Training modules and challenges for school students to attract bright minds.",
    utilisedAmountLakh: 0,
    purchasesFor: "",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 8,
    budgetHead: "Industry-Academia Ideathons",
    amountText: "Rs. 15 Lakhs/year for 2 years (Total 30 lakhs)",
    amount: 3000000,
    description: "Ideathons to connect industry with academia and improve UG student perception.",
    utilisedAmountLakh: 10.05,
    purchasesFor: "Events of CiPD with ECE; 1.5 for Telecom Shakti",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 9,
    budgetHead: "Digital Whiteboards for Faculty",
    amountText: "Rs. 10 Lakhs",
    amount: 1000000,
    description: "Equip offices with digital whiteboards for enhanced discussions and screen-sharing, air-purifiers.",
    utilisedAmountLakh: 3.9,
    purchasesFor: "Panel & Camera",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 10,
    budgetHead: "Embedded Systems Equipment",
    amountText: "Rs. 29 Lakhs",
    amount: 2900000,
    description: "Advanced embedded system boards for teaching and research.",
    utilisedAmountLakh: 1.28634,
    purchasesFor: "",
    invoice: "Not attached",
    invoiceUrl: "",
  },
  {
    id: 11,
    budgetHead: "Nanofabrication Consumables",
    amountText: "Rs. 15 Lakhs/year for 2 years (Total 30 lakhs)",
    amount: 3000000,
    description: "Contingency budget for consumables and imported items for VLSI labs.",
    utilisedAmountLakh: 0,
    purchasesFor: "",
    invoice: "Not attached",
    invoiceUrl: "",
  },
];

const initialForm: FormState = {
  date: "",
  budgetHead: "",
  approvedAmount: "",
  utilizedAmount: "",
  description: "",
  purchasesFor: "",
  invoiceName: "",
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
  const [records, setRecords] = useState<IncomeRecord[]>(seedRecords);
  const [form, setForm] = useState<FormState>(initialForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [headFilter, setHeadFilter] = useState("all");
  const [financialYearFilter, setFinancialYearFilter] = useState(() => getFinancialYear(new Date().toISOString()));
  const [expandedHeads, setExpandedHeads] = useState(() => new Set<string>());
  const [showHeadSuggestions, setShowHeadSuggestions] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const formSectionRef = useRef<HTMLElement>(null);

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

  function saveIncomeRecord(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setError("");
      setSuccess("");
      validateForm();

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
        invoice: form.invoiceName.trim() || "Not Attached",
        invoiceUrl: "",
      };

      if (editingId) {
        setRecords((current) => current.map((record) => (record.id === editingId ? payload : record)));
      } else {
        setRecords((current) => [payload, ...current]);
      }

      setEditingId(null);
      setForm(initialForm);
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
    });
    requestAnimationFrame(() => {
      formSectionRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }

  function deleteIncomeRecord(record: IncomeRecord) {
    const entriesUnderHead = records.filter(
      (item) => item.budgetHead === record.budgetHead && getRecordFinancialYear(item) === getRecordFinancialYear(record),
    ).length;
    const message =
      entriesUnderHead === 1
        ? `Warning: this is the only entry under "${record.budgetHead}" for ${getRecordFinancialYear(record)}. Deleting it will also remove the budget head. Continue?`
        : "Delete only this accumulated-income entry?";
    if (!window.confirm(message)) return;
    setRecords((current) => current.filter((item) => item.id !== record.id));
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
              Invoice / Document Name
              <input className="rounded-lg border border-slate-300 px-3 py-2" value={form.invoiceName} onChange={(event) => updateField("invoiceName", event.target.value)} placeholder="invoice.pdf" />
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
                <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50" type="button" onClick={() => { setEditingId(null); setForm(initialForm); }}>
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
                <th className="border-b border-slate-200 px-4 py-3">S. N.</th>
                <th className="border-b border-slate-200 px-4 py-3">Budget Head</th>
                <th className="border-b border-slate-200 px-4 py-3">Total Amount Approved (INR)</th>
                <th className="border-b border-slate-200 px-4 py-3">Utilized (INR)</th>
                <th className="border-b border-slate-200 px-4 py-3">Remaining (INR)</th>
                <th className="border-b border-slate-200 px-4 py-3">Entries</th>
              </tr>
            </thead>
            <tbody>
              {groupedBudgetHeads.map((group, index) => {
                const isExpanded = expandedHeads.has(group.key);
                return (
                  <Fragment key={group.key}>
                    <tr className="hover:bg-slate-50">
                      <td className="border-b border-slate-100 px-4 py-3">{index + 1}</td>
                      <td className="border-b border-slate-100 px-4 py-3">
                        <button className="flex w-full items-start gap-2 text-left font-semibold text-teal-900" type="button" aria-expanded={isExpanded} onClick={() => toggleBudgetHead(group.key)}>
                          <span>{isExpanded ? "v" : ">"}</span>
                          <span>{group.head}</span>
                        </button>
                      </td>
                      <td className="border-b border-slate-100 px-4 py-3">{inrNumber.format(group.approvedAmount)}</td>
                      <td className="border-b border-slate-100 px-4 py-3">{inrNumber.format(group.utilizedAmount)}</td>
                      <td className="border-b border-slate-100 px-4 py-3">{inrNumber.format(group.remainingAmount)}</td>
                      <td className="border-b border-slate-100 px-4 py-3">{group.entries.length}</td>
                    </tr>
                    {isExpanded && (
                      <tr>
                        <td className="border-b border-slate-100 bg-slate-50 p-4" colSpan={6}>
                          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
                            <table className="min-w-[860px] w-full text-sm">
                              <thead className="bg-slate-50 text-left text-slate-700">
                                <tr>
                                  <th className="border-b border-slate-200 px-3 py-2">S. N.</th>
                                  <th className="border-b border-slate-200 px-3 py-2">Date</th>
                                  <th className="border-b border-slate-200 px-3 py-2">Description</th>
                                  <th className="border-b border-slate-200 px-3 py-2">Purchases For</th>
                                  <th className="border-b border-slate-200 px-3 py-2">Utilized (INR)</th>
                                  <th className="border-b border-slate-200 px-3 py-2">Invoice</th>
                                  {isAdmin && <th className="border-b border-slate-200 px-3 py-2">Actions</th>}
                                </tr>
                              </thead>
                              <tbody>
                                {group.entries.map((record, entryIndex) => (
                                  <tr key={record.id}>
                                    <td className="border-b border-slate-100 px-3 py-2">{entryIndex + 1}</td>
                                    <td className="border-b border-slate-100 px-3 py-2">{record.date || "Not recorded"}</td>
                                    <td className="border-b border-slate-100 px-3 py-2">{record.description || record.notes || "No description"}</td>
                                    <td className="border-b border-slate-100 px-3 py-2">{record.purchasesFor || "-"}</td>
                                    <td className="border-b border-slate-100 px-3 py-2">{inrNumber.format(getUtilizedAmount(record))}</td>
                                    <td className="border-b border-slate-100 px-3 py-2">{record.invoice || "Not Attached"}</td>
                                    {isAdmin && (
                                      <td className="border-b border-slate-100 px-3 py-2">
                                        <div className="flex flex-wrap gap-2">
                                          <button className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold hover:bg-slate-50" type="button" onClick={() => editRecord(record)}>
                                            Edit
                                          </button>
                                          <button className="rounded border border-slate-300 px-2 py-1 text-xs font-semibold hover:bg-slate-50" type="button" onClick={() => deleteIncomeRecord(record)}>
                                            Delete
                                          </button>
                                        </div>
                                      </td>
                                    )}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
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
