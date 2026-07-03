import { apiDelete, apiGet, apiPostForm, apiPostJson, apiPutJson } from "../../services/api";

export function listBudgetRecords<T>(collection: "income" | "expenses" | "inventory") {
  return apiGet<T[]>(`/budget/${collection}`);
}

export function createBudgetRecord<T>(collection: "income" | "expenses" | "inventory", body: unknown) {
  return apiPostJson<T>(`/budget/${collection}`, body);
}

export function updateBudgetRecord<T>(collection: "income" | "expenses" | "inventory", id: number, body: unknown) {
  return apiPutJson<T>(`/budget/${collection}/${id}`, body);
}

export function deleteBudgetRecord(collection: "income" | "expenses" | "inventory", id: number) {
  return apiDelete(`/budget/${collection}/${id}`);
}

export function uploadBudgetInvoice(file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiPostForm<{ invoice: string; invoiceUrl: string }>("/budget/invoices", form);
}

export async function downloadBudgetInvoice(invoiceUrl: string, fileName = "invoice.pdf") {
  const token = localStorage.getItem("access_token");
  const headers: HeadersInit = token ? { Authorization: `Bearer ${token}` } : {};
  const res = await fetch(`/api/v1${invoiceUrl}`, { headers });
  if (!res.ok) throw new Error("Invoice download failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}
