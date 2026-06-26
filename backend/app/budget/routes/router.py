from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.budget.models.entities import BudgetExpense, BudgetIncome, BudgetInventory
from app.budget.schemas import (
    BudgetExpenseCreate,
    BudgetExpenseResponse,
    BudgetExpenseUpdate,
    BudgetIncomeCreate,
    BudgetIncomeResponse,
    BudgetIncomeUpdate,
    BudgetInventoryCreate,
    BudgetInventoryResponse,
    BudgetInventoryUpdate,
    BudgetSummaryResponse,
    BudgetUploadResponse,
)
from app.budget.services.budget_service import (
    budget_invoice_dir,
    create_expense,
    create_income,
    create_inventory,
    delete_record,
    get_expense,
    get_income,
    get_inventory,
    list_expenses,
    list_income,
    list_inventory,
    store_invoice,
    update_expense,
    update_income,
    update_inventory,
)
from app.database.models.user import User, UserRole
from app.database.session import get_db

router = APIRouter(prefix="/budget", tags=["budget"])


@router.get("/summary", response_model=BudgetSummaryResponse)
def budget_summary(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    income = list_income(db)
    expenses = list_expenses(db)
    inventory = list_inventory(db)

    income_groups: dict[str, dict[str, float]] = {}
    for record in income:
        key = f"{record.financial_year or ''}:{record.budget_head}"
        current = income_groups.setdefault(key, {"approved": 0, "used": 0})
        current["approved"] = max(current["approved"], float(record.amount or 0))
        current["used"] += float(record.utilised_amount_lakh or 0) * 100000

    expense_groups: dict[str, dict[str, float]] = {}
    for record in expenses:
        key = f"{record.date.year if record.date else ''}:{record.head}"
        current = expense_groups.setdefault(key, {"approved": 0, "used": 0})
        current["approved"] = max(current["approved"], float(record.budget_lakh or 0) * 100000)
        current["used"] += float(record.amount or 0)

    return BudgetSummaryResponse(
        income_remaining=sum(max(row["approved"] - row["used"], 0) for row in income_groups.values()),
        expense_remaining=sum(max(row["approved"] - row["used"], 0) for row in expense_groups.values()),
        inventory_value=sum(float(row.amount or 0) for row in inventory),
        income_heads=len(income_groups),
        expense_heads=len(expense_groups),
        inventory_items=len(inventory),
    )


@router.get("/income", response_model=list[BudgetIncomeResponse])
def read_income(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return list_income(db)


@router.post("/income", response_model=BudgetIncomeResponse, status_code=status.HTTP_201_CREATED)
def add_income(
    body: BudgetIncomeCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    return create_income(db, body, user)


@router.put("/income/{record_id}", response_model=BudgetIncomeResponse)
def edit_income(
    record_id: int,
    body: BudgetIncomeUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_income(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Income record not found")
    return update_income(db, row, body, user)


@router.delete("/income/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_income(
    record_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_income(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Income record not found")
    delete_record(db, row)


@router.get("/expenses", response_model=list[BudgetExpenseResponse])
def read_expenses(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return list_expenses(db)


@router.post("/expenses", response_model=BudgetExpenseResponse, status_code=status.HTTP_201_CREATED)
def add_expense(
    body: BudgetExpenseCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    return create_expense(db, body, user)


@router.put("/expenses/{record_id}", response_model=BudgetExpenseResponse)
def edit_expense(
    record_id: int,
    body: BudgetExpenseUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_expense(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Expense record not found")
    return update_expense(db, row, body, user)


@router.delete("/expenses/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_expense(
    record_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_expense(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Expense record not found")
    delete_record(db, row)


@router.get("/inventory", response_model=list[BudgetInventoryResponse])
def read_inventory(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return list_inventory(db)


@router.post("/inventory", response_model=BudgetInventoryResponse, status_code=status.HTTP_201_CREATED)
def add_inventory(
    body: BudgetInventoryCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    return create_inventory(db, body, user)


@router.put("/inventory/{record_id}", response_model=BudgetInventoryResponse)
def edit_inventory(
    record_id: int,
    body: BudgetInventoryUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_inventory(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    return update_inventory(db, row, body, user)


@router.delete("/inventory/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_inventory(
    record_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
):
    row = get_inventory(db, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    delete_record(db, row)


@router.post("/uploads", response_model=BudgetUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    _: Annotated[User, Depends(require_roles(UserRole.admin))],
    file: Annotated[UploadFile, File(...)],
):
    try:
        file_name, stored_name, url = await store_invoice(file)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BudgetUploadResponse(file_name=file_name, stored_name=stored_name, url=url)


@router.get("/uploads/{stored_name}")
def download_invoice(
    stored_name: str,
    _: Annotated[User, Depends(get_current_user)],
):
    safe_name = stored_name.replace("/", "").replace("\\", "")
    path = budget_invoice_dir() / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Invoice not found")
    return FileResponse(path)

