from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class BudgetIncome(Base):
    __tablename__ = "budget_income"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    financial_year: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    budget_head: Mapped[str] = mapped_column(Text, nullable=False)
    amount_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    utilised_amount_lakh: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    purchases_for: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice: Mapped[str | None] = mapped_column(String(512), nullable=True)
    invoice_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BudgetExpense(Base):
    __tablename__ = "budget_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    head: Mapped[str] = mapped_column(Text, nullable=False)
    budget_lakh: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    expenses_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    utilized_lakh: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    balance_lakh: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    vendor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    invoice: Mapped[str | None] = mapped_column(String(512), nullable=True)
    invoice_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class BudgetInventory(Base):
    __tablename__ = "budget_inventory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item: Mapped[str] = mapped_column(String(255), nullable=False, default="Inventory Purchase")
    category: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_given: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purchase_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    invoice: Mapped[str | None] = mapped_column(String(512), nullable=True)
    invoice_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
