from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.budget.models.entities import BudgetExpense, BudgetIncome, BudgetInventory
from app.budget.schemas import (
    BudgetExpenseCreate,
    BudgetExpenseUpdate,
    BudgetIncomeCreate,
    BudgetIncomeUpdate,
    BudgetInventoryCreate,
    BudgetInventoryUpdate,
)
from app.config import get_settings
from app.database.models.user import User

ALLOWED_INVOICE_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}
MAX_INVOICE_BYTES = 10 * 1024 * 1024


def _actor(user: User) -> str:
    return user.email or str(user.id)


def list_income(db: Session) -> list[BudgetIncome]:
    stmt = select(BudgetIncome).order_by(BudgetIncome.date.desc(), BudgetIncome.id.desc())
    return list(db.scalars(stmt).all())


def get_income(db: Session, record_id: int) -> BudgetIncome | None:
    return db.get(BudgetIncome, record_id)


def create_income(db: Session, body: BudgetIncomeCreate, user: User) -> BudgetIncome:
    row = BudgetIncome(**body.model_dump(), created_by=_actor(user))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_income(db: Session, row: BudgetIncome, body: BudgetIncomeUpdate, user: User) -> BudgetIncome:
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_by = _actor(user)
    db.commit()
    db.refresh(row)
    return row


def list_expenses(db: Session) -> list[BudgetExpense]:
    stmt = select(BudgetExpense).order_by(BudgetExpense.date.desc(), BudgetExpense.id.desc())
    return list(db.scalars(stmt).all())


def get_expense(db: Session, record_id: int) -> BudgetExpense | None:
    return db.get(BudgetExpense, record_id)


def create_expense(db: Session, body: BudgetExpenseCreate, user: User) -> BudgetExpense:
    row = BudgetExpense(**body.model_dump(), created_by=_actor(user))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_expense(db: Session, row: BudgetExpense, body: BudgetExpenseUpdate, user: User) -> BudgetExpense:
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_by = _actor(user)
    db.commit()
    db.refresh(row)
    return row


def list_inventory(db: Session) -> list[BudgetInventory]:
    stmt = select(BudgetInventory).order_by(BudgetInventory.purchase_date.desc(), BudgetInventory.id.desc())
    return list(db.scalars(stmt).all())


def get_inventory(db: Session, record_id: int) -> BudgetInventory | None:
    return db.get(BudgetInventory, record_id)


def create_inventory(db: Session, body: BudgetInventoryCreate, user: User) -> BudgetInventory:
    row = BudgetInventory(**body.model_dump(), created_by=_actor(user))
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def update_inventory(
    db: Session,
    row: BudgetInventory,
    body: BudgetInventoryUpdate,
    user: User,
) -> BudgetInventory:
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    row.updated_by = _actor(user)
    db.commit()
    db.refresh(row)
    return row


def delete_record(db: Session, row) -> None:
    db.delete(row)
    db.commit()


def budget_invoice_dir() -> Path:
    root = Path(get_settings().upload_dir) / "budget_invoices"
    root.mkdir(parents=True, exist_ok=True)
    return root


async def store_invoice(file: UploadFile) -> tuple[str, str, str]:
    content_type = file.content_type or ""
    extension = ALLOWED_INVOICE_TYPES.get(content_type)
    if not extension:
        raise ValueError("Only PDF, PNG, and JPG invoices are allowed")

    payload = await file.read()
    if len(payload) > MAX_INVOICE_BYTES:
        raise ValueError("Invoice file must be 10MB or smaller")

    original_name = Path(file.filename or "invoice").name
    stored_name = f"{uuid4().hex}{extension}"
    destination = budget_invoice_dir() / stored_name
    destination.write_bytes(payload)
    return original_name, stored_name, f"/budget/uploads/{stored_name}"

