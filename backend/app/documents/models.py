from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


def utc_now() -> datetime:
    return datetime.now(UTC)


class DocumentRecord(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index(
            "ix_documents_duplicate_key",
            "vendor_name",
            "invoice_number",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_filename: Mapped[str] = mapped_column(String(255), unique=True)
    content_type: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), index=True)
    vendor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    classification: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    extraction: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    document_review: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    validation: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    gl_suggestion: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    selected_gl_account_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )


class CorrectionThreadRecord(Base):
    """One outbound correction attempt and its optional supplier reply."""

    __tablename__ = "correction_threads"
    __table_args__ = (
        Index("ix_correction_threads_document_attempt", "document_id", "attempt_number"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(
        ForeignKey("documents.id"), index=True
    )
    attempt_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(30), index=True)
    to_email: Mapped[str] = mapped_column(String(320))
    subject: Mapped[str] = mapped_column(String(998))
    body: Mapped[str] = mapped_column(Text)
    issue_codes: Mapped[list[str]] = mapped_column(JSON)
    nylas_thread_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )
    outbound_nylas_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    inbound_nylas_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, unique=True
    )
    inbound_from_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
