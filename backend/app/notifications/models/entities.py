from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    created_by_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    attachments: Mapped[list["NotificationAttachment"]] = relationship(
        "NotificationAttachment", back_populates="notification", cascade="all, delete-orphan"
    )
    recipients: Mapped[list["NotificationRecipient"]] = relationship(
        "NotificationRecipient", back_populates="notification", cascade="all, delete-orphan"
    )


class NotificationAttachment(Base):
    __tablename__ = "notification_attachments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    storage_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notification: Mapped[Notification] = relationship("Notification", back_populates="attachments")


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"
    __table_args__ = (UniqueConstraint("notification_id", "user_id", name="uq_notification_recipient"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    notification_id: Mapped[int] = mapped_column(ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    email_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    email_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    notification: Mapped[Notification] = relationship("Notification", back_populates="recipients")
