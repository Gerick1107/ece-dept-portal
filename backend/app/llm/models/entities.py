from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class LlmInsightsCache(Base):
    __tablename__ = "llm_insights_cache"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_id: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)
    course_id: Mapped[str] = mapped_column(String(512), nullable=False, index=True)  # course_title
    prompt_used: Mapped[str | None] = mapped_column(Text, nullable=True)
    llm_response: Mapped[str] = mapped_column(Text, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
