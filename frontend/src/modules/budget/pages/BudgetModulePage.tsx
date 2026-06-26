import { useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import {
  createExpense,
  createIncome,
  createInventory,
  deleteExpense,
  deleteIncome,
  deleteInventory,
  fetchBudgetDataset,
  updateExpense,
  updateIncome,
  updateInventory,
  uploadBudgetInvoice,
} from "../services/budgetApi";
import type {
  BudgetDataset,
  BudgetExpensePayload,
  BudgetExpenseRecord,
  BudgetIncomePayload,
  BudgetIncomeRecord,
  BudgetInventoryPayload,
  BudgetInventoryRecord,
} from "../types";

const currency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

const sections = ["income", "expenses", "inventory"] as const;
type Section = (typeof sections)[number];

function financialYear(dateValue?: string | null) {
  if (!dateValue) return "";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return "";
  const start = date.getMonth() + 1 >= 4 ? date.getFullYear() : date.getFullYear() - 1;
  return `${start}-${start + 1}`;
}

function invoiceHref(url?: string | null) {
  if (!url) return "";
  if (url.startsWith("http")) return url;
  return `/api/v1${url}`;
}

function readNumber(value: FormDataEntryValue | null) {
  return Number(value || 0);
}

export default function BudgetModulePage() {
  const { user } = useAuth();
  const params = useParams();
  const navigate = useNavigate();
  const isAdmin = user?.role === "admin";
  const activeSection = sections.includes(params.section as Section)
    ? (params.section as Section)
    : "income";
  const [dataset, setDataset] = useState<BudgetDataset>({
    income: [],
    expenses: [],
    inventory: [],
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [editing, setEditing] = useState<{ section: Section; id: number } | null>(null);

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      setDataset(await fetchBudgetDataset());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load budget data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const summary = useMemo(() => {
    const incomeGroups = new Map<string, { approved: number; used: number }>();
    dataset.income.forEach((record) => {
      const year = record.financial_year || financialYear(record.date);
      const key = `${year}:${record.budget_head}`;
      const current = incomeGroups.get(key) ?? { approved: 0, used: 0 };
      current.approved = Math.max(current.approved, Number(record.amount || 0));
      current.used += Number(record.utilised_amount_lakh || 0) * 100000;
      incomeGroups.set(key, current);
    });

    const expenseGroups = new Map<string, { approved: number; used: number }>();
    dataset.expenses.forEach((record) => {
      const key = `${financialYear(record.date)}:${record.head}`;
      const current = expenseGroups.get(key) ?? { approved: 0, used: 0 };
      current.approved = Math.max(current.approved, Number(record.budget_lakh || 0) * 100000);
      current.used += Number(record.amount || 0);
      expenseGroups.set(key, current);
    });

    return {
      incomeRemaining: [...incomeGroups.values()].reduce(
        (sum, item) => sum + Math.max(item.approved - item.used, 0),
        0,
      ),
      expenseRemaining: [...expenseGroups.values()].reduce(
        (sum, item) => sum + Math.max(item.approved - item.used, 0),
        0,
      ),
      inventoryValue: dataset.inventory.reduce((sum, item) => sum + Number(item.amount || 0), 0),
    };
  }, [dataset]);

  function matches(record: Record<string, unknown>) {
    const normalized = query.trim().toLowerCase();
    if (!normalized) return true;
    return Object.values(record).some((value) =>
      String(value ?? "").toLowerCase().includes(normalized),
    );
  }

  async function attachInvoice<T extends { invoice?: string | null; invoice_url?: string | null }>(
    payload: T,
    file: File | null,
  ): Promise<T> {
    if (!file) return payload;
    const upload = await uploadBudgetInvoice(file);
    return { ...payload, invoice: upload.file_name, invoice_url: upload.url };
  }

  async function submitIncome(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const payload = await attachInvoice<BudgetIncomePayload>(
      {
        date: String(form.get("date") || ""),
        financial_year: financialYear(String(form.get("date") || "")),
        budget_head: String(form.get("budget_head") || "").trim(),
        amount: readNumber(form.get("amount")),
        amount_text: String(form.get("amount_text") || ""),
        description: String(form.get("description") || ""),
        utilised_amount_lakh: readNumber(form.get("utilised_amount")) / 100000,
        purchases_for: String(form.get("purchases_for") || ""),
        invoice: "",
        invoice_url: "",
      },
      (form.get("invoice") as File | null)?.size ? (form.get("invoice") as File) : null,
    );
    await saveRecord("income", payload, event.currentTarget);
  }

  async function submitExpense(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const amount = readNumber(form.get("amount"));
    const budgetLakh = readNumber(form.get("budget_lakh"));
    const payload = await attachInvoice<BudgetExpensePayload>(
      {
        head: String(form.get("head") || "").trim(),
        budget_lakh: budgetLakh,
        expenses_description: String(form.get("expenses_description") || ""),
        utilized_lakh: amount / 100000,
        balance_lakh: Math.max(budgetLakh - amount / 100000, 0),
        vendor: String(form.get("vendor") || "ECE Department"),
        date: String(form.get("date") || ""),
        amount,
        status: String(form.get("status") || "Pending"),
        invoice: "",
        invoice_url: "",
      },
      (form.get("invoice") as File | null)?.size ? (form.get("invoice") as File) : null,
    );
    await saveRecord("expenses", payload, event.currentTarget);
  }

  async function submitInventory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const quantity = readNumber(form.get("quantity"));
    const quantityGiven = readNumber(form.get("quantity_given"));
    const payload = await attachInvoice<BudgetInventoryPayload>(
      {
        item: String(form.get("item") || "Inventory Purchase"),
        category: String(form.get("category") || "").trim(),
        quantity,
        quantity_given: quantityGiven,
        remaining_quantity: Math.max(quantity - quantityGiven, 0),
        location: String(form.get("location") || "Not specified"),
        purchase_date: String(form.get("purchase_date") || ""),
        amount: readNumber(form.get("amount")),
        invoice: "",
        invoice_url: "",
      },
      (form.get("invoice") as File | null)?.size ? (form.get("invoice") as File) : null,
    );
    await saveRecord("inventory", payload, event.currentTarget);
  }

  async function saveRecord(
    section: Section,
    payload: BudgetIncomePayload | BudgetExpensePayload | BudgetInventoryPayload,
    form: HTMLFormElement,
  ) {
    setSaving(true);
    setError("");
    try {
      if (section === "income") {
        editing?.section === "income"
          ? await updateIncome(editing.id, payload as BudgetIncomePayload)
          : await createIncome(payload as BudgetIncomePayload);
      }
      if (section === "expenses") {
        editing?.section === "expenses"
          ? await updateExpense(editing.id, payload as BudgetExpensePayload)
          : await createExpense(payload as BudgetExpensePayload);
      }
      if (section === "inventory") {
        editing?.section === "inventory"
          ? await updateInventory(editing.id, payload as BudgetInventoryPayload)
          : await createInventory(payload as BudgetInventoryPayload);
      }
      form.reset();
      setEditing(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  async function removeRecord(section: Section, id: number) {
    if (!window.confirm("Delete this budget record?")) return;
    setError("");
    if (section === "income") await deleteIncome(id);
    if (section === "expenses") await deleteExpense(id);
    if (section === "inventory") await deleteInventory(id);
    await refresh();
  }

  function openSection(section: Section) {
    navigate(section === "income" ? "/budget/income" : `/budget/${section}`);
  }

  const incomeRows = dataset.income.filter((row) => matches(row as unknown as Record<string, unknown>));
  const expenseRows = dataset.expenses.filter((row) => matches(row as unknown as Record<string, unknown>));
  const inventoryRows = dataset.inventory.filter((row) => matches(row as unknown as Record<string, unknown>));

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-6">
      <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-xs uppercase tracking-wide text-teal-700 font-semibold">ECE Department</p>
          <h1 className="text-2xl font-semibold text-slate-900">Budget</h1>
          <p className="text-sm text-slate-600">
            Department income, expenditure, inventory, and invoice records.
          </p>
        </div>
        <input
          className="w-full md:w-72 rounded-lg border border-slate-300 px-3 py-2 text-sm"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search budget records"
        />
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <SummaryCard label="Income Remaining" value={currency.format(summary.incomeRemaining)} />
        <SummaryCard label="Expense Remaining" value={currency.format(summary.expenseRemaining)} />
        <SummaryCard label="Inventory Value" value={currency.format(summary.inventoryValue)} />
      </div>

      <div className="flex flex-wrap gap-2">
        <SectionButton active={activeSection === "income"} onClick={() => openSection("income")}>
          Accumulated Income
        </SectionButton>
        <SectionButton active={activeSection === "expenses"} onClick={() => openSection("expenses")}>
          Expenditure Budget
        </SectionButton>
        <SectionButton active={activeSection === "inventory"} onClick={() => openSection("inventory")}>
          Inventory
        </SectionButton>
      </div>

      {error && <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
      {loading ? <p className="text-center text-slate-500">Loading budget records...</p> : null}

      {!loading && activeSection === "income" && (
        <IncomeSection
          isAdmin={isAdmin}
          rows={incomeRows}
          editing={editing?.section === "income" ? dataset.income.find((row) => row.id === editing.id) : undefined}
          saving={saving}
          onSubmit={submitIncome}
          onEdit={(id) => setEditing({ section: "income", id })}
          onDelete={(id) => void removeRecord("income", id)}
        />
      )}
      {!loading && activeSection === "expenses" && (
        <ExpenseSection
          isAdmin={isAdmin}
          rows={expenseRows}
          editing={editing?.section === "expenses" ? dataset.expenses.find((row) => row.id === editing.id) : undefined}
          saving={saving}
          onSubmit={submitExpense}
          onEdit={(id) => setEditing({ section: "expenses", id })}
          onDelete={(id) => void removeRecord("expenses", id)}
        />
      )}
      {!loading && activeSection === "inventory" && (
        <InventorySection
          isAdmin={isAdmin}
          rows={inventoryRows}
          editing={editing?.section === "inventory" ? dataset.inventory.find((row) => row.id === editing.id) : undefined}
          saving={saving}
          onSubmit={submitInventory}
          onEdit={(id) => setEditing({ section: "inventory", id })}
          onDelete={(id) => void removeRecord("inventory", id)}
        />
      )}
    </div>
  );
}

function SummaryCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <strong className="mt-1 block text-xl text-slate-900">{value}</strong>
    </div>
  );
}

function SectionButton({
  active,
  children,
  onClick,
}: {
  active: boolean;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-lg px-3 py-2 text-sm transition-colors ${
        active ? "bg-teal-800 text-white" : "bg-white text-slate-700 border border-slate-200 hover:bg-slate-50"
      }`}
    >
      {children}
    </button>
  );
}

function Field({
  label,
  name,
  type = "text",
  defaultValue,
  required = false,
}: {
  label: string;
  name: string;
  type?: string;
  defaultValue?: string | number | null;
  required?: boolean;
}) {
  return (
    <label className="text-sm text-slate-700">
      <span className="mb-1 block font-medium">{label}</span>
      <input
        required={required}
        type={type}
        name={name}
        defaultValue={defaultValue ?? ""}
        className="w-full rounded-lg border border-slate-300 px-3 py-2"
      />
    </label>
  );
}

function InvoiceCell({ row }: { row: { invoice?: string | null; invoice_url?: string | null } }) {
  const href = invoiceHref(row.invoice_url);
  if (!href) return <span className="text-slate-400">Not attached</span>;
  return (
    <a className="font-medium text-teal-700 hover:text-teal-900" href={href} target="_blank" rel="noreferrer">
      {row.invoice || "View invoice"}
    </a>
  );
}

function IncomeSection({
  isAdmin,
  rows,
  editing,
  saving,
  onSubmit,
  onEdit,
  onDelete,
}: {
  isAdmin: boolean;
  rows: BudgetIncomeRecord[];
  editing?: BudgetIncomeRecord;
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <section className="space-y-4">
      {isAdmin && (
        <RecordForm
          key={editing?.id ?? "new-income"}
          title={editing ? "Edit Income Record" : "Add Income Record"}
          onSubmit={onSubmit}
          saving={saving}
        >
          <Field label="Date" name="date" type="date" defaultValue={editing?.date} />
          <Field label="Budget Head" name="budget_head" defaultValue={editing?.budget_head} required />
          <Field label="Approved Amount" name="amount" type="number" defaultValue={editing?.amount} required />
          <Field label="Amount Text" name="amount_text" defaultValue={editing?.amount_text} />
          <Field
            label="Utilised Amount"
            name="utilised_amount"
            type="number"
            defaultValue={editing ? Number(editing.utilised_amount_lakh || 0) * 100000 : 0}
          />
          <Field label="Purchases For" name="purchases_for" defaultValue={editing?.purchases_for} />
          <Field label="Description" name="description" defaultValue={editing?.description} />
          <Field label="Invoice" name="invoice" type="file" />
        </RecordForm>
      )}
      <Table
        headers={["Budget Head", "Approved", "Utilised", "Remaining", "Invoice", "Actions"]}
        rows={rows.map((row) => [
          row.budget_head,
          currency.format(row.amount),
          currency.format(Number(row.utilised_amount_lakh || 0) * 100000),
          currency.format(Math.max(row.amount - Number(row.utilised_amount_lakh || 0) * 100000, 0)),
          <InvoiceCell row={row} />,
          isAdmin ? <Actions id={row.id} onEdit={onEdit} onDelete={onDelete} /> : null,
        ])}
      />
    </section>
  );
}

function ExpenseSection({
  isAdmin,
  rows,
  editing,
  saving,
  onSubmit,
  onEdit,
  onDelete,
}: {
  isAdmin: boolean;
  rows: BudgetExpenseRecord[];
  editing?: BudgetExpenseRecord;
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <section className="space-y-4">
      {isAdmin && (
        <RecordForm
          key={editing?.id ?? "new-expense"}
          title={editing ? "Edit Expense Record" : "Add Expense Record"}
          onSubmit={onSubmit}
          saving={saving}
        >
          <Field label="Date" name="date" type="date" defaultValue={editing?.date} required />
          <Field label="Budget Head" name="head" defaultValue={editing?.head} required />
          <Field label="Budget Lakh" name="budget_lakh" type="number" defaultValue={editing?.budget_lakh} required />
          <Field label="Amount" name="amount" type="number" defaultValue={editing?.amount} required />
          <Field label="Vendor" name="vendor" defaultValue={editing?.vendor || "ECE Department"} />
          <Field label="Status" name="status" defaultValue={editing?.status || "Pending"} />
          <Field label="Description" name="expenses_description" defaultValue={editing?.expenses_description} />
          <Field label="Invoice" name="invoice" type="file" />
        </RecordForm>
      )}
      <Table
        headers={["Budget Head", "Budget", "Utilised", "Balance", "Status", "Invoice", "Actions"]}
        rows={rows.map((row) => [
          row.head,
          currency.format(Number(row.budget_lakh || 0) * 100000),
          currency.format(row.amount),
          currency.format(Math.max(Number(row.budget_lakh || 0) * 100000 - row.amount, 0)),
          row.status,
          <InvoiceCell row={row} />,
          isAdmin ? <Actions id={row.id} onEdit={onEdit} onDelete={onDelete} /> : null,
        ])}
      />
    </section>
  );
}

function InventorySection({
  isAdmin,
  rows,
  editing,
  saving,
  onSubmit,
  onEdit,
  onDelete,
}: {
  isAdmin: boolean;
  rows: BudgetInventoryRecord[];
  editing?: BudgetInventoryRecord;
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <section className="space-y-4">
      {isAdmin && (
        <RecordForm
          key={editing?.id ?? "new-inventory"}
          title={editing ? "Edit Inventory Record" : "Add Inventory Record"}
          onSubmit={onSubmit}
          saving={saving}
        >
          <Field label="Purchase Date" name="purchase_date" type="date" defaultValue={editing?.purchase_date} required />
          <Field label="Item" name="item" defaultValue={editing?.item || "Inventory Purchase"} required />
          <Field label="Category" name="category" defaultValue={editing?.category} required />
          <Field label="Quantity" name="quantity" type="number" defaultValue={editing?.quantity} required />
          <Field label="Quantity Given" name="quantity_given" type="number" defaultValue={editing?.quantity_given || 0} />
          <Field label="Location" name="location" defaultValue={editing?.location || "Not specified"} />
          <Field label="Amount" name="amount" type="number" defaultValue={editing?.amount} required />
          <Field label="Invoice" name="invoice" type="file" />
        </RecordForm>
      )}
      <Table
        headers={["Category", "Quantity", "Given", "Remaining", "Amount", "Invoice", "Actions"]}
        rows={rows.map((row) => [
          row.category,
          row.quantity,
          row.quantity_given,
          Math.max(row.quantity - row.quantity_given, 0),
          currency.format(row.amount),
          <InvoiceCell row={row} />,
          isAdmin ? <Actions id={row.id} onEdit={onEdit} onDelete={onDelete} /> : null,
        ])}
      />
    </section>
  );
}

function RecordForm({
  title,
  children,
  saving,
  onSubmit,
}: {
  title: string;
  children: ReactNode;
  saving: boolean;
  onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}) {
  return (
    <form className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm" onSubmit={onSubmit}>
      <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      <div className="mt-4 grid gap-4 md:grid-cols-2">{children}</div>
      <button
        type="submit"
        disabled={saving}
        className="mt-4 rounded-lg bg-teal-800 px-4 py-2 text-sm font-medium text-white hover:bg-teal-700 disabled:opacity-60"
      >
        {saving ? "Saving..." : "Save"}
      </button>
    </form>
  );
}

function Actions({
  id,
  onEdit,
  onDelete,
}: {
  id: number;
  onEdit: (id: number) => void;
  onDelete: (id: number) => void;
}) {
  return (
    <div className="flex gap-2">
      <button className="text-sm font-medium text-teal-700" type="button" onClick={() => onEdit(id)}>
        Edit
      </button>
      <button className="text-sm font-medium text-red-600" type="button" onClick={() => onDelete(id)}>
        Delete
      </button>
    </div>
  );
}

function Table({ headers, rows }: { headers: string[]; rows: ReactNode[][] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {headers.map((header) => (
              <th key={header} className="px-3 py-2 text-left font-semibold text-slate-600">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.length === 0 ? (
            <tr>
              <td className="px-3 py-6 text-center text-slate-500" colSpan={headers.length}>
                No records found.
              </td>
            </tr>
          ) : (
            rows.map((row, index) => (
              <tr key={index}>
                {row.map((cell, cellIndex) => (
                  <td key={cellIndex} className="px-3 py-2 align-top text-slate-700">
                    {cell}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
