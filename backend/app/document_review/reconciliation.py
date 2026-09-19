"""Deterministic merge: Document Intelligence stays primary, the LLM fills only gaps."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal, NamedTuple

from app.document_review.schemas import (
    DocumentReview,
    FieldComparison,
    FieldSource,
    LlmDocumentExtraction,
)
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt

ValueKind = Literal["text", "identifier", "date", "amount"]


class FieldSpec(NamedTuple):
    field: str
    llm_field: str
    label: str
    kind: ValueKind


INVOICE_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("vendor_name", "vendor_name", "Supplier", "text"),
    FieldSpec("vendor_vat_id", "vendor_vat_id", "Supplier VAT number", "identifier"),
    FieldSpec("customer_name", "customer_name", "Customer", "text"),
    FieldSpec("customer_vat_id", "customer_vat_id", "Customer VAT number", "identifier"),
    FieldSpec("invoice_number", "invoice_number", "Invoice number", "identifier"),
    FieldSpec("purchase_order", "purchase_order", "Purchase order", "identifier"),
    FieldSpec("invoice_date", "invoice_date", "Invoice date", "date"),
    FieldSpec("due_date", "due_date", "Due date", "date"),
    FieldSpec("currency", "currency", "Currency", "identifier"),
    FieldSpec("subtotal", "subtotal", "Subtotal", "amount"),
    FieldSpec("total_tax", "total_tax", "VAT total", "amount"),
    FieldSpec("invoice_total", "total", "Invoice total", "amount"),
)

RECEIPT_FIELDS: tuple[FieldSpec, ...] = (
    FieldSpec("merchant_name", "vendor_name", "Merchant", "text"),
    FieldSpec("transaction_date", "invoice_date", "Transaction date", "date"),
    FieldSpec("expense_category", "expense_category", "Expense category", "text"),
    FieldSpec("currency", "currency", "Currency", "identifier"),
    FieldSpec("subtotal", "subtotal", "Subtotal", "amount"),
    FieldSpec("total_tax", "total_tax", "VAT total", "amount"),
    FieldSpec("total", "total", "Receipt total", "amount"),
)


def _shown(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_text(value: str) -> str:
    return "".join(character for character in value.casefold() if character.isalnum())


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", value.upper())


def _normalize_date(value: str) -> str:
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError:
        return value.strip().casefold()


def _normalize_amount(value: str) -> str:
    try:
        return str(Decimal(value.replace(",", ".")).normalize())
    except InvalidOperation:
        return value.strip().casefold()


NORMALIZERS: dict[ValueKind, Callable[[str], str]] = {
    "text": _normalize_text,
    "identifier": _normalize_identifier,
    "date": _normalize_date,
    "amount": _normalize_amount,
}


def _parse(kind: ValueKind, value: str) -> object | None:
    """Turn an LLM string into the domain type; None when it does not parse."""
    if kind == "date":
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    if kind == "amount":
        try:
            return Decimal(value.replace(",", ".")).quantize(Decimal("0.01"))
        except InvalidOperation:
            return None
    return value.strip() or None


def _compare(spec: FieldSpec, primary: str | None, secondary: str | None) -> FieldComparison:
    if primary is None and secondary is None:
        status = "missing_in_both"
    elif secondary is None:
        status = "missing_in_llm"
    elif primary is None:
        status = "missing_in_document_intelligence"
    else:
        normalize = NORMALIZERS[spec.kind]
        status = "match" if normalize(primary) == normalize(secondary) else "different"
    return FieldComparison(
        field=spec.field,
        label=spec.label,
        status=status,
        document_intelligence_value=primary,
        llm_value=secondary,
    )


def _specs(document: Invoice | Receipt) -> tuple[FieldSpec, ...]:
    return INVOICE_FIELDS if isinstance(document, Invoice) else RECEIPT_FIELDS


def primary_field_sources(document: Invoice | Receipt) -> dict[str, FieldSource]:
    """Mark every present Document Intelligence value as primary."""
    return {
        spec.field: "document_intelligence"
        for spec in _specs(document)
        if _shown(getattr(document, spec.field)) is not None
    }


def merge_document[D: (Invoice, Receipt)](
    document: D,
    secondary: LlmDocumentExtraction,
) -> tuple[D, dict[str, FieldSource], DocumentReview]:
    """Fill missing Document Intelligence fields from the LLM; never overwrite a present one."""
    specs = _specs(document)
    merged = document.model_dump()
    field_sources = primary_field_sources(document)
    comparisons: list[FieldComparison] = []
    fallback_fields: list[str] = []

    for spec in specs:
        primary = _shown(getattr(document, spec.field))
        llm_value = _shown(getattr(secondary, spec.llm_field))
        comparisons.append(_compare(spec, primary, llm_value))

        if primary is not None or llm_value is None:
            continue
        parsed = _parse(spec.kind, llm_value)
        if parsed is None:
            continue
        merged[spec.field] = parsed
        field_sources[spec.field] = "llm_fallback"
        fallback_fields.append(spec.field)

    review = DocumentReview(
        extraction=secondary,
        comparisons=comparisons,
        fallback_fields=fallback_fields,
    )
    return type(document).model_validate(merged), field_sources, review
