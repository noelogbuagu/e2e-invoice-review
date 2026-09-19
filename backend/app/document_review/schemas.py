from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

FieldSource = Literal["document_intelligence", "llm_fallback", "human"]

ComparisonStatus = Literal[
    "match",
    "different",
    "missing_in_llm",
    "missing_in_document_intelligence",
    "missing_in_both",
]


class LlmDocumentExtraction(BaseModel):
    """What the independent reviewer read from the original file.

    Values are plain strings so the model never has to guess number or date
    formats. The deterministic merge parses them into the domain types.
    Receipts reuse the invoice-shaped names: merchant -> vendor_name,
    transaction date -> invoice_date, receipt total -> total.
    """

    document_kind: Literal["invoice", "receipt", "unsupported"]
    vendor_name: str | None
    vendor_vat_id: str | None
    customer_name: str | None
    customer_vat_id: str | None
    invoice_number: str | None
    purchase_order: str | None
    invoice_date: str | None
    due_date: str | None
    currency: str | None
    subtotal: str | None
    total_tax: str | None
    total: str | None
    expense_category: str | None
    summary: str


class FieldComparison(BaseModel):
    field: str
    label: str
    status: ComparisonStatus
    document_intelligence_value: str | None
    llm_value: str | None


class DocumentReview(BaseModel):
    """Secondary-reviewer evidence shown under the Document Intelligence section."""

    extraction: LlmDocumentExtraction | None = None
    comparisons: list[FieldComparison] = Field(default_factory=list)
    fallback_fields: list[str] = Field(default_factory=list)
    error_message: str | None = None
