from __future__ import annotations

import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.budget.services.budget_service import (
    create_expense,
    create_income,
    create_inventory,
    delete_row,
    expense_to_dict,
    get_expense,
    get_income,
    get_inventory,
    income_to_dict,
    inventory_to_dict,
    list_expenses,
    list_income,
    list_inventory,
    update_expense,
    update_income,
    update_inventory,
)
from app.config import get_settings
from app.database.models.user import User, UserRole
from app.database.session import get_db

router = APIRouter(prefix="/budget", tags=["budget"])
MAX_INVOICE_BYTES = 10 * 1024 * 1024


class BudgetPayload(BaseModel):
    model_config = ConfigDict(extra="allow")


def _invoice_dir() -> Path:
    path = Path(get_settings().upload_dir) / "budget-invoices"
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post("/invoices", status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF invoice files are allowed")
    payload = await file.read()
    if len(payload) > MAX_INVOICE_BYTES:
        raise HTTPException(status_code=400, detail="Invoice file too large (max 10 MB)")

    stored_name = f"{uuid.uuid4().hex}.pdf"
    (_invoice_dir() / stored_name).write_bytes(payload)
    return {
        "invoice": file.filename,
        "invoiceUrl": f"/budget/invoices/{stored_name}/download",
    }


@router.get("/invoices/{filename}/download")
def download_invoice(
    filename: str,
    _: Annotated[User, Depends(get_current_user)],
):
    path = _invoice_dir() / Path(filename).name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Invoice file not found")
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.get("/income")
def budget_income(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return [income_to_dict(row) for row in list_income(db)]


@router.post("/income", status_code=status.HTTP_201_CREATED)
def add_budget_income(
    body: BudgetPayload,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    try:
        return income_to_dict(create_income(db, body.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/income/{row_id}")
def edit_budget_income(
    row_id: int,
    body: BudgetPayload,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    row = get_income(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Budget income entry not found")
    try:
        return income_to_dict(update_income(db, row, body.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/income/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_budget_income(
    row_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    row = get_income(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Budget income entry not found")
    delete_row(db, row)


@router.get("/expenses")
def budget_expenses(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return [expense_to_dict(row) for row in list_expenses(db)]


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
def add_budget_expense(
    body: BudgetPayload,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    try:
        return expense_to_dict(create_expense(db, body.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/expenses/{row_id}")
def edit_budget_expense(
    row_id: int,
    body: BudgetPayload,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    row = get_expense(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Budget expense entry not found")
    try:
        return expense_to_dict(update_expense(db, row, body.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/expenses/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_budget_expense(
    row_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    row = get_expense(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Budget expense entry not found")
    delete_row(db, row)


@router.get("/inventory")
def budget_inventory(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(get_current_user)],
):
    return [inventory_to_dict(row) for row in list_inventory(db)]


@router.post("/inventory", status_code=status.HTTP_201_CREATED)
def add_budget_inventory(
    body: BudgetPayload,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    try:
        return inventory_to_dict(create_inventory(db, body.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/inventory/{row_id}")
def edit_budget_inventory(
    row_id: int,
    body: BudgetPayload,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    row = get_inventory(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Budget inventory entry not found")
    try:
        return inventory_to_dict(update_inventory(db, row, body.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/inventory/{row_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_budget_inventory(
    row_id: int,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[User, Depends(require_roles(UserRole.hod))],
):
    row = get_inventory(db, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Budget inventory entry not found")
    delete_row(db, row)
