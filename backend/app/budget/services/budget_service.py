from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budget.models.entities import BudgetExpense, BudgetIncome, BudgetInventory

BudgetRow = TypeVar("BudgetRow", BudgetIncome, BudgetExpense, BudgetInventory)


def _str_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_value(value: Any, default: float = 0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def _int_value(value: Any, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(value)


def list_income(db: Session) -> list[BudgetIncome]:
    return list(db.scalars(select(BudgetIncome).order_by(BudgetIncome.id.asc())).all())


def list_expenses(db: Session) -> list[BudgetExpense]:
    return list(db.scalars(select(BudgetExpense).order_by(BudgetExpense.id.asc())).all())


def list_inventory(db: Session) -> list[BudgetInventory]:
    return list(db.scalars(select(BudgetInventory).order_by(BudgetInventory.id.asc())).all())


def get_income(db: Session, row_id: int) -> BudgetIncome | None:
    return db.get(BudgetIncome, row_id)


def get_expense(db: Session, row_id: int) -> BudgetExpense | None:
    return db.get(BudgetExpense, row_id)


def get_inventory(db: Session, row_id: int) -> BudgetInventory | None:
    return db.get(BudgetInventory, row_id)


def income_to_dict(row: BudgetIncome) -> dict[str, Any]:
    return {
        "id": row.id,
        "date": row.date,
        "financialYear": row.financial_year,
        "budgetHead": row.budget_head,
        "amountText": row.amount_text,
        "amount": row.amount,
        "description": row.description,
        "utilisedAmountLakh": row.utilised_amount_lakh,
        "purchasesFor": row.purchases_for,
        "invoice": row.invoice,
        "invoiceUrl": row.invoice_url,
    }


def expense_to_dict(row: BudgetExpense) -> dict[str, Any]:
    return {
        "id": row.id,
        "head": row.head,
        "budgetLakh": row.budget_lakh,
        "expensesDescription": row.expenses_description,
        "utilizedLakh": row.utilized_lakh,
        "balanceLakh": row.balance_lakh,
        "vendor": row.vendor,
        "date": row.date,
        "amount": row.amount,
        "invoice": row.invoice,
        "invoiceUrl": row.invoice_url,
        "status": row.status,
    }


def inventory_to_dict(row: BudgetInventory) -> dict[str, Any]:
    return {
        "id": row.id,
        "item": row.item,
        "category": row.category,
        "quantity": row.quantity,
        "quantityGiven": row.quantity_given,
        "remainingQuantity": max(row.quantity - row.quantity_given, 0),
        "location": row.location,
        "purchaseDate": row.purchase_date,
        "amount": row.amount,
        "invoice": row.invoice,
        "invoiceUrl": row.invoice_url,
    }


def create_income(db: Session, data: Mapping[str, Any]) -> BudgetIncome:
    row = BudgetIncome()
    _apply_income(row, data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_expense(db: Session, data: Mapping[str, Any]) -> BudgetExpense:
    row = BudgetExpense()
    _apply_expense(row, data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def create_inventory(db: Session, data: Mapping[str, Any]) -> BudgetInventory:
    row = BudgetInventory()
    _apply_inventory(row, data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_income(db: Session, row: BudgetIncome, data: Mapping[str, Any]) -> BudgetIncome:
    _apply_income(row, data)
    db.commit()
    db.refresh(row)
    return row


def update_expense(db: Session, row: BudgetExpense, data: Mapping[str, Any]) -> BudgetExpense:
    _apply_expense(row, data)
    db.commit()
    db.refresh(row)
    return row


def update_inventory(db: Session, row: BudgetInventory, data: Mapping[str, Any]) -> BudgetInventory:
    _apply_inventory(row, data)
    db.commit()
    db.refresh(row)
    return row


def delete_row(db: Session, row: BudgetRow) -> None:
    db.delete(row)
    db.commit()


def _apply_income(row: BudgetIncome, data: Mapping[str, Any]) -> None:
    budget_head = _str_or_none(data.get("budgetHead"))
    if not budget_head:
        raise ValueError("Budget head is required")
    amount = _float_value(data.get("amount"))
    if amount <= 0:
        raise ValueError("Approved amount must be greater than zero")
    utilised = _float_value(data.get("utilisedAmountLakh"))
    if utilised < 0:
        raise ValueError("Utilized amount must be zero or greater")
    row.date = _str_or_none(data.get("date"))
    row.financial_year = _str_or_none(data.get("financialYear"))
    row.budget_head = budget_head
    row.amount_text = _str_or_none(data.get("amountText"))
    row.amount = amount
    row.description = _str_or_none(data.get("description"))
    row.utilised_amount_lakh = utilised
    row.purchases_for = _str_or_none(data.get("purchasesFor"))
    row.invoice = _str_or_none(data.get("invoice")) or "Not Attached"
    row.invoice_url = _str_or_none(data.get("invoiceUrl"))


def _apply_expense(row: BudgetExpense, data: Mapping[str, Any]) -> None:
    head = _str_or_none(data.get("head"))
    if not head:
        raise ValueError("Budget head is required")
    budget_lakh = _float_value(data.get("budgetLakh"))
    amount = _float_value(data.get("amount"))
    if budget_lakh <= 0:
        raise ValueError("Budget must be greater than zero")
    if amount < 0:
        raise ValueError("Utilized amount must be zero or greater")
    row.head = head
    row.budget_lakh = budget_lakh
    row.expenses_description = _str_or_none(data.get("expensesDescription"))
    row.utilized_lakh = _float_value(data.get("utilizedLakh"), amount / 100000)
    row.balance_lakh = _float_value(data.get("balanceLakh"), max(budget_lakh - row.utilized_lakh, 0))
    row.vendor = _str_or_none(data.get("vendor")) or "ECE Department"
    row.date = _str_or_none(data.get("date"))
    row.amount = amount
    row.invoice = _str_or_none(data.get("invoice")) or "Not Attached"
    row.invoice_url = _str_or_none(data.get("invoiceUrl"))
    row.status = _str_or_none(data.get("status")) or "Pending"


def _apply_inventory(row: BudgetInventory, data: Mapping[str, Any]) -> None:
    category = _str_or_none(data.get("category"))
    if not category:
        raise ValueError("Category is required")
    quantity = _int_value(data.get("quantity"))
    quantity_given = _int_value(data.get("quantityGiven"))
    amount = _float_value(data.get("amount"))
    if quantity <= 0:
        raise ValueError("Total quantity must be greater than zero")
    if quantity_given < 0 or quantity_given > quantity:
        raise ValueError("Quantity given must be between zero and total quantity")
    if amount <= 0:
        raise ValueError("Purchase amount must be greater than zero")
    row.item = _str_or_none(data.get("item")) or "Inventory Purchase"
    row.category = category
    row.quantity = quantity
    row.quantity_given = quantity_given
    row.location = _str_or_none(data.get("location")) or "Not specified"
    row.purchase_date = _str_or_none(data.get("purchaseDate"))
    row.amount = amount
    row.invoice = _str_or_none(data.get("invoice")) or "Not Attached"
    row.invoice_url = _str_or_none(data.get("invoiceUrl"))
