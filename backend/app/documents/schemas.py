from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.accounting.catalog import GlAccountCode, GlAccountSuggestion
from app.document_review.schemas import DocumentReview
from app.pipeline.base import DocumentClassification, ExtractionState, ValidationState

DocumentStatus = Literal[
    "processing",
    "ready",
    "needs_review",
    "approved",
    "rejected",
    "failed",
]
DECIDED_STATUSES: frozenset[str] = frozenset({"approved", "rejected"})
REVIEWABLE_STATUSES: frozenset[str] = frozenset({"ready", "needs_review"})


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str
    status: DocumentStatus
    classification: DocumentClassification | None = None
    extraction: ExtractionState | None = None
    document_review: DocumentReview | None = None
    validation: ValidationState | None = None
    gl_suggestion: GlAccountSuggestion | None = None
    selected_gl_account_code: GlAccountCode | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceCorrection(BaseModel):
    """Scalar invoice fields Maya may edit. Only the keys sent are applied."""

    model_config = ConfigDict(extra="forbid")

    vendor_name: str | None = None
    vendor_vat_id: str | None = None
    customer_name: str | None = None
    customer_vat_id: str | None = None
    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    purchase_order: str | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    total_tax: Decimal | None = None
    invoice_total: Decimal | None = None


class ReceiptCorrection(BaseModel):
    """Scalar receipt fields Maya may edit. Only the keys sent are applied."""

    model_config = ConfigDict(extra="forbid")

    merchant_name: str | None = None
    transaction_date: date | None = None
    expense_category: str | None = None
    currency: str | None = None
    subtotal: Decimal | None = None
    total_tax: Decimal | None = None
    total: Decimal | None = None


class DocumentCorrectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice: InvoiceCorrection | None = None
    receipt: ReceiptCorrection | None = None


class GlSelectionRequest(BaseModel):
    gl_account_code: str


class DecisionRequest(BaseModel):
    decision: Literal["approved", "rejected"]
