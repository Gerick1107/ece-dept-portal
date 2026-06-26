export type BudgetInvoiceFields = {
  invoice?: string | null;
  invoice_url?: string | null;
};

export type BudgetIncomeRecord = BudgetInvoiceFields & {
  id: number;
  date?: string | null;
  financial_year?: string | null;
  budget_head: string;
  amount: number;
  amount_text?: string | null;
  description?: string | null;
  utilised_amount_lakh: number;
  purchases_for?: string | null;
};

export type BudgetIncomePayload = Omit<BudgetIncomeRecord, "id">;

export type BudgetExpenseRecord = BudgetInvoiceFields & {
  id: number;
  head: string;
  budget_lakh: number;
  expenses_description?: string | null;
  utilized_lakh: number;
  balance_lakh: number;
  vendor: string;
  date: string;
  amount: number;
  status: "Pending" | "Approved" | "Rejected" | string;
};

export type BudgetExpensePayload = Omit<BudgetExpenseRecord, "id">;

export type BudgetInventoryRecord = BudgetInvoiceFields & {
  id: number;
  item: string;
  category: string;
  quantity: number;
  quantity_given: number;
  remaining_quantity: number;
  location?: string | null;
  purchase_date: string;
  amount: number;
};

export type BudgetInventoryPayload = Omit<BudgetInventoryRecord, "id">;

export type BudgetSummary = {
  income_remaining: number;
  expense_remaining: number;
  inventory_value: number;
  income_heads: number;
  expense_heads: number;
  inventory_items: number;
};

export type BudgetDataset = {
  income: BudgetIncomeRecord[];
  expenses: BudgetExpenseRecord[];
  inventory: BudgetInventoryRecord[];
};

export type UploadResponse = {
  file_name: string;
  stored_name: string;
  url: string;
};

