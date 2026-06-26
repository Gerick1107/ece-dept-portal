from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field, model_validator


class BudgetInvoiceFields(BaseModel):
    invoice: str | None = None
    invoice_url: str | None = None


class BudgetIncomeBase(BudgetInvoiceFields):
    date: date | None = None
    financial_year: str | None = Field(default=None, max_length=20)
    budget_head: str = Field(min_length=1, max_length=500)
    amount: float = Field(ge=0)
    amount_text: str | None = Field(default=None, max_length=120)
    description: str | None = None
    utilised_amount_lakh: float = Field(default=0, ge=0)
    purchases_for: str | None = None


class BudgetIncomeCreate(BudgetIncomeBase):
    pass


class BudgetIncomeUpdate(BudgetIncomeBase):
    pass


class BudgetIncomeResponse(BudgetIncomeBase):
    id: int

    model_config = {"from_attributes": True}


class BudgetExpenseBase(BudgetInvoiceFields):
    head: str = Field(min_length=1, max_length=700)
    budget_lakh: float = Field(default=0, ge=0)
    expenses_description: str | None = None
    utilized_lakh: float = Field(default=0, ge=0)
    balance_lakh: float = Field(default=0, ge=0)
    vendor: str = Field(default="ECE Department", min_length=1, max_length=255)
    date: date
    amount: float = Field(default=0, ge=0)
    status: str = Field(default="Pending", max_length=40)


class BudgetExpenseCreate(BudgetExpenseBase):
    pass


class BudgetExpenseUpdate(BudgetExpenseBase):
    pass


class BudgetExpenseResponse(BudgetExpenseBase):
    id: int

    model_config = {"from_attributes": True}


class BudgetInventoryBase(BudgetInvoiceFields):
    item: str = Field(default="Inventory Purchase", min_length=1, max_length=255)
    category: str = Field(min_length=1, max_length=255)
    quantity: int = Field(ge=0)
    quantity_given: int = Field(default=0, ge=0)
    remaining_quantity: int = Field(default=0, ge=0)
    location: str | None = Field(default=None, max_length=255)
    purchase_date: date
    amount: float = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_quantities(self) -> "BudgetInventoryBase":
        if self.quantity_given > self.quantity:
            raise ValueError("Quantity given cannot exceed total quantity")
        self.remaining_quantity = max(self.quantity - self.quantity_given, 0)
        return self


class BudgetInventoryCreate(BudgetInventoryBase):
    pass


class BudgetInventoryUpdate(BudgetInventoryBase):
    pass


class BudgetInventoryResponse(BudgetInventoryBase):
    id: int

    model_config = {"from_attributes": True}


class BudgetSummaryResponse(BaseModel):
    income_remaining: float
    expense_remaining: float
    inventory_value: float
    income_heads: int
    expense_heads: int
    inventory_items: int


class BudgetUploadResponse(BaseModel):
    file_name: str
    stored_name: str
    url: str

