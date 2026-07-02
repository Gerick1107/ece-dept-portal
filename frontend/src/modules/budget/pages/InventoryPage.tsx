import { useMemo, useState } from "react";
import { useAuth } from "../../auth/AuthContext";

type InventoryItem = {
  id: number;
  item: string;
  category: string;
  quantity: number;
  quantityGiven?: number;
  location: string;
  purchaseDate: string;
  amount: number;
  invoice?: string;
};

type InventoryForm = {
  category: string;
  customCategory: string;
  totalQuantity: string;
  quantityGiven: string;
  purchaseDate: string;
  amount: string;
  invoiceName: string;
};

const seedItems: InventoryItem[] = [
  {
    id: 1,
    item: "Digital Storage Oscilloscope",
    category: "Lab Equipment",
    quantity: 6,
    quantityGiven: 0,
    location: "ECE Lab 204",
    purchaseDate: "2026-04-18",
    amount: 420000,
    invoice: "tek-scope-invoice.pdf",
  },
  {
    id: 2,
    item: "Soldering Station",
    category: "Tools",
    quantity: 12,
    quantityGiven: 0,
    location: "ECE Workshop",
    purchaseDate: "2026-05-07",
    amount: 48000,
    invoice: "soldering-stations.pdf",
  },
  {
    id: 3,
    item: "FPGA Trainer Kit",
    category: "Teaching Aid",
    quantity: 10,
    quantityGiven: 0,
    location: "Digital Systems Lab",
    purchaseDate: "2026-06-04",
    amount: 310000,
    invoice: "fpga-kits.pdf",
  },
];

const categories = ["Lab Equipment", "Tools", "Consumables", "Teaching Aid", "Furniture"];
const initialForm: InventoryForm = {
  category: "",
  customCategory: "",
  totalQuantity: "",
  quantityGiven: "",
  purchaseDate: "",
  amount: "",
  invoiceName: "",
};

const currency = new Intl.NumberFormat("en-IN", {
  style: "currency",
  currency: "INR",
  maximumFractionDigits: 0,
});

function getFinancialYear(dateValue?: string) {
  if (!dateValue) return "";
  const date = new Date(dateValue);
  if (Number.isNaN(date.getTime())) return "";
  const year = date.getFullYear();
  const startYear = date.getMonth() + 1 >= 4 ? year : year - 1;
  return `${startYear}-${startYear + 1}`;
}

function formatDate(dateValue: string) {
  const date = new Date(dateValue);
  return Number.isNaN(date.getTime()) ? dateValue : date.toLocaleDateString("en-GB");
}

function matchesSearch(item: InventoryItem, query: string) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return true;
  return Object.values(item).some((value) => String(value || "").toLowerCase().includes(normalized));
}

function exportCsv(rows: InventoryItem[]) {
  const columns = ["Purchase Date", "Category", "Total Quantity", "Quantity Given", "Remaining Quantity", "Amount", "Invoice"];
  const body = rows.map((item) => [
    formatDate(item.purchaseDate),
    item.category,
    item.quantity,
    Number(item.quantityGiven || 0),
    Math.max(item.quantity - Number(item.quantityGiven || 0), 0),
    item.amount,
    item.invoice || "Not Attached",
  ]);
  const csv = [columns, ...body].map((line) => line.map((cell) => `"${String(cell).replaceAll('"', '""')}"`).join(",")).join("\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = "ece-inventory-register.csv";
  link.click();
  URL.revokeObjectURL(url);
}

export default function InventoryPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin" || user?.role === "hod";
  const [items, setItems] = useState<InventoryItem[]>(seedItems);
  const [form, setForm] = useState<InventoryForm>(initialForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [financialYearFilter, setFinancialYearFilter] = useState(() => getFinancialYear(new Date().toISOString()));
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  const categoryOptions = useMemo(
    () => [...new Set([...categories, ...items.map((item) => item.category).filter(Boolean)])],
    [items],
  );
  const financialYearOptions = useMemo(
    () => [...new Set(items.map((item) => getFinancialYear(item.purchaseDate)).filter(Boolean))],
    [items],
  );
  const filteredItems = useMemo(
    () =>
      items.filter((item) => {
        const matchesCategory = categoryFilter === "all" || item.category === categoryFilter;
        const matchesYear = financialYearFilter === "all" || getFinancialYear(item.purchaseDate) === financialYearFilter;
        return matchesCategory && matchesYear && matchesSearch(item, search);
      }),
    [categoryFilter, financialYearFilter, items, search],
  );
  const inventoryValue = filteredItems.reduce((sum, item) => sum + Number(item.amount || 0), 0);
  const remainingQuantity = Math.max(Number(form.totalQuantity || 0) - Number(form.quantityGiven || 0), 0);

  function saveInventoryItem(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    try {
      setSuccess("");
      setError("");
      if (Number(form.totalQuantity) <= 0) throw new Error("Total quantity must be greater than zero");
      if (Number(form.quantityGiven) < 0) throw new Error("Quantity given must be zero or greater");
      if (Number(form.quantityGiven) > Number(form.totalQuantity)) throw new Error("Quantity given cannot exceed total quantity");
      if (Number(form.amount) <= 0) throw new Error("Purchase amount must be greater than zero");

      const category = form.category === "Other" ? form.customCategory.trim() : form.category;
      const item: InventoryItem = {
        id: editingId ?? Math.max(0, ...items.map((record) => record.id)) + 1,
        item: "Inventory Purchase",
        category,
        quantity: Number(form.totalQuantity),
        quantityGiven: Number(form.quantityGiven || 0),
        location: "Not specified",
        purchaseDate: form.purchaseDate,
        amount: Number(form.amount),
        invoice: form.invoiceName.trim() || "Not Attached",
      };
      setItems((current) => (editingId ? current.map((record) => (record.id === editingId ? item : record)) : [item, ...current]));
      setEditingId(null);
      setForm(initialForm);
      setSuccess("Saved Successfully");
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "Save failed");
    }
  }

  function editItem(item: InventoryItem) {
    setEditingId(item.id);
    setSuccess("");
    setError("");
    setForm({
      category: item.category,
      customCategory: "",
      totalQuantity: String(item.quantity || 0),
      quantityGiven: String(item.quantityGiven || 0),
      purchaseDate: item.purchaseDate,
      amount: String(item.amount),
      invoiceName: item.invoice && item.invoice !== "Not Attached" ? item.invoice : "",
    });
  }

  function deleteItem(item: InventoryItem) {
    if (!window.confirm("Delete this inventory record?")) return;
    setItems((current) => current.filter((record) => record.id !== item.id));
  }

  return (
    <main className="space-y-6">
      <section className="grid gap-6 rounded-lg border border-slate-200 bg-white p-6 shadow-sm lg:grid-cols-[1fr_320px]">
        <div>
          <p className="text-xs font-bold uppercase tracking-wide text-teal-700">Assets and Purchases</p>
          <h2 className="mt-2 text-2xl font-semibold text-slate-950">Inventory</h2>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Track equipment, consumables, teaching aids, purchase references, and invoice details.
          </p>
        </div>
        <div className="rounded-lg border border-teal-100 bg-teal-50 p-5">
          <span className="text-xs font-bold uppercase text-slate-500">
            Total Amount Spent · {financialYearFilter === "all" ? "All Financial Years" : `FY ${financialYearFilter}`}
          </span>
          <strong className="mt-2 block text-2xl text-teal-900">{currency.format(inventoryValue)}</strong>
        </div>
      </section>

      {isAdmin && (
        <section className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5">
            <h3 className="text-lg font-semibold text-slate-950">{editingId ? "Edit Inventory Item" : "Add Inventory Item"}</h3>
            <p className="mt-1 text-sm text-slate-600">Invoice upload is optional in the original portal; this first pass stores the invoice name.</p>
          </div>
          <form className="grid gap-4 md:grid-cols-2" onSubmit={saveInventoryItem}>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Purchase Date
              <input className="rounded-lg border border-slate-300 px-3 py-2" required type="date" value={form.purchaseDate} onChange={(event) => setForm((current) => ({ ...current, purchaseDate: event.target.value }))} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Category
              <select className="rounded-lg border border-slate-300 px-3 py-2" required value={form.category} onChange={(event) => setForm((current) => ({ ...current, category: event.target.value }))}>
                <option value="">Select category</option>
                {categoryOptions.map((category) => <option key={category}>{category}</option>)}
                <option>Other</option>
              </select>
            </label>
            {form.category === "Other" && (
              <label className="grid gap-1 text-sm font-medium text-slate-700">
                Enter Category
                <input className="rounded-lg border border-slate-300 px-3 py-2" required value={form.customCategory} onChange={(event) => setForm((current) => ({ ...current, customCategory: event.target.value }))} />
              </label>
            )}
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Total Quantity
              <input className="rounded-lg border border-slate-300 px-3 py-2" required min="1" type="number" value={form.totalQuantity} onChange={(event) => setForm((current) => ({ ...current, totalQuantity: event.target.value }))} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Quantity Given
              <input className="rounded-lg border border-slate-300 px-3 py-2" required min="0" type="number" value={form.quantityGiven} onChange={(event) => setForm((current) => ({ ...current, quantityGiven: event.target.value }))} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Remaining Quantity
              <input className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-2" readOnly value={remainingQuantity} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Purchase Amount
              <input className="rounded-lg border border-slate-300 px-3 py-2" required min="1" type="number" value={form.amount} onChange={(event) => setForm((current) => ({ ...current, amount: event.target.value }))} />
            </label>
            <label className="grid gap-1 text-sm font-medium text-slate-700">
              Invoice / Document Name
              <input className="rounded-lg border border-slate-300 px-3 py-2" value={form.invoiceName} onChange={(event) => setForm((current) => ({ ...current, invoiceName: event.target.value }))} />
            </label>
            <div className="flex flex-wrap gap-2 md:col-span-2">
              <button className="rounded-lg bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-600" type="submit">
                {editingId ? "Update Inventory Item" : "Save Inventory Item"}
              </button>
              {editingId && (
                <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium" type="button" onClick={() => { setEditingId(null); setForm(initialForm); }}>
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
            <h3 className="text-lg font-semibold text-slate-950">Inventory Register</h3>
            <p className="mt-1 text-sm text-slate-600">Search, filter, export, edit, or delete inventory records.</p>
          </div>
          <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-medium hover:bg-slate-50" type="button" onClick={() => exportCsv(filteredItems)}>
            Export CSV
          </button>
        </div>
        <div className="mb-5 grid gap-3 md:grid-cols-3">
          <label className="grid gap-1 text-sm font-medium text-slate-700">
            Search
            <input className="rounded-lg border border-slate-300 px-3 py-2" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search category, invoice..." />
          </label>
          <label className="grid gap-1 text-sm font-medium text-slate-700">
            Financial Year
            <select className="rounded-lg border border-slate-300 px-3 py-2" value={financialYearFilter} onChange={(event) => setFinancialYearFilter(event.target.value)}>
              <option value="all">All financial years</option>
              {financialYearOptions.map((year) => <option key={year}>{year}</option>)}
            </select>
          </label>
          <label className="grid gap-1 text-sm font-medium text-slate-700">
            Category
            <select className="rounded-lg border border-slate-300 px-3 py-2" value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}>
              <option value="all">All categories</option>
              {categoryOptions.map((category) => <option key={category}>{category}</option>)}
            </select>
          </label>
        </div>
        <div className="overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-[840px] w-full text-sm">
            <thead className="bg-teal-50 text-left text-teal-950">
              <tr>
                <th className="border-b border-slate-200 px-4 py-3">Purchase Date</th>
                <th className="border-b border-slate-200 px-4 py-3">Category</th>
                <th className="border-b border-slate-200 px-4 py-3">Total Quantity</th>
                <th className="border-b border-slate-200 px-4 py-3">Quantity Given</th>
                <th className="border-b border-slate-200 px-4 py-3">Remaining</th>
                <th className="border-b border-slate-200 px-4 py-3">Amount</th>
                <th className="border-b border-slate-200 px-4 py-3">Invoice</th>
                {isAdmin && <th className="border-b border-slate-200 px-4 py-3">Actions</th>}
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item) => (
                <tr key={item.id}>
                  <td className="border-b border-slate-100 px-4 py-3">{formatDate(item.purchaseDate)}</td>
                  <td className="border-b border-slate-100 px-4 py-3">{item.category}</td>
                  <td className="border-b border-slate-100 px-4 py-3">{item.quantity}</td>
                  <td className="border-b border-slate-100 px-4 py-3">{Number(item.quantityGiven || 0)}</td>
                  <td className="border-b border-slate-100 px-4 py-3">{Math.max(item.quantity - Number(item.quantityGiven || 0), 0)}</td>
                  <td className="border-b border-slate-100 px-4 py-3">{currency.format(item.amount)}</td>
                  <td className="border-b border-slate-100 px-4 py-3">{item.invoice || "Not Attached"}</td>
                  {isAdmin && (
                    <td className="border-b border-slate-100 px-4 py-3">
                      <div className="flex gap-2">
                        <button className="rounded border px-2 py-1 text-xs font-semibold" type="button" onClick={() => editItem(item)}>Edit</button>
                        <button className="rounded border px-2 py-1 text-xs font-semibold" type="button" onClick={() => deleteItem(item)}>Delete</button>
                      </div>
                    </td>
                  )}
                </tr>
              ))}
              {filteredItems.length === 0 && (
                <tr>
                  <td className="px-4 py-4 text-slate-500" colSpan={isAdmin ? 8 : 7}>No inventory records found.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}
