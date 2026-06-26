import {
  apiDelete,
  apiGet,
  apiPostForm,
  apiPostJson,
  apiPutJson,
} from "../../../services/api";
import type {
  BudgetDataset,
  BudgetExpensePayload,
  BudgetExpenseRecord,
  BudgetIncomePayload,
  BudgetIncomeRecord,
  BudgetInventoryPayload,
  BudgetInventoryRecord,
  BudgetSummary,
  UploadResponse,
} from "../types";

export async function fetchBudgetDataset(): Promise<BudgetDataset> {
  const [income, expenses, inventory] = await Promise.all([
    apiGet<BudgetIncomeRecord[]>("/budget/income"),
    apiGet<BudgetExpenseRecord[]>("/budget/expenses"),
    apiGet<BudgetInventoryRecord[]>("/budget/inventory"),
  ]);
  return { income, expenses, inventory };
}

export function fetchBudgetSummary(): Promise<BudgetSummary> {
  return apiGet<BudgetSummary>("/budget/summary");
}

export function createIncome(body: BudgetIncomePayload): Promise<BudgetIncomeRecord> {
  return apiPostJson<BudgetIncomeRecord>("/budget/income", body);
}

export function updateIncome(id: number, body: BudgetIncomePayload): Promise<BudgetIncomeRecord> {
  return apiPutJson<BudgetIncomeRecord>(`/budget/income/${id}`, body);
}

export function deleteIncome(id: number): Promise<void> {
  return apiDelete(`/budget/income/${id}`);
}

export function createExpense(body: BudgetExpensePayload): Promise<BudgetExpenseRecord> {
  return apiPostJson<BudgetExpenseRecord>("/budget/expenses", body);
}

export function updateExpense(id: number, body: BudgetExpensePayload): Promise<BudgetExpenseRecord> {
  return apiPutJson<BudgetExpenseRecord>(`/budget/expenses/${id}`, body);
}

export function deleteExpense(id: number): Promise<void> {
  return apiDelete(`/budget/expenses/${id}`);
}

export function createInventory(
  body: BudgetInventoryPayload,
): Promise<BudgetInventoryRecord> {
  return apiPostJson<BudgetInventoryRecord>("/budget/inventory", body);
}

export function updateInventory(
  id: number,
  body: BudgetInventoryPayload,
): Promise<BudgetInventoryRecord> {
  return apiPutJson<BudgetInventoryRecord>(`/budget/inventory/${id}`, body);
}

export function deleteInventory(id: number): Promise<void> {
  return apiDelete(`/budget/inventory/${id}`);
}

export function uploadBudgetInvoice(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  return apiPostForm<UploadResponse>("/budget/uploads", form);
}

