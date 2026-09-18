from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel
from stdnum.eu import vat

from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt

TOTAL_TOLERANCE = Decimal("0.01")


class IssueSeverity(StrEnum):
    error = "error"
    warning = "warning"


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: IssueSeverity = IssueSeverity.error


def _vat_issue(
    value: str | None,
    *,
    required: bool,
    missing_code: str,
    invalid_code: str,
    label: str,
) -> ValidationIssue | None:
    if value is None or not value.strip():
        if required:
            return ValidationIssue(
                code=missing_code,
                message=f"{label} VAT ID is required",
            )
        return None
    if not vat.is_valid(value):
        return ValidationIssue(
            code=invalid_code,
            message=f"{label} VAT ID is not a valid EU VAT number",
        )
    return None


def _totals_issue(
    subtotal: Decimal | None,
    total_tax: Decimal | None,
    total: Decimal | None,
    code: str,
) -> ValidationIssue | None:
    if subtotal is None or total_tax is None or total is None:
        return None
    if abs((subtotal + total_tax) - total) > TOTAL_TOLERANCE:
        return ValidationIssue(
            code=code,
            message=f"Subtotal {subtotal} + VAT {total_tax} does not equal total {total}",
        )
    return None


def validate_invoice(invoice: Invoice) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    vendor_vat = _vat_issue(
        invoice.vendor_vat_id,
        required=True,
        missing_code="vendor_vat_id_required",
        invalid_code="vendor_vat_id_invalid",
        label="Vendor",
    )
    if vendor_vat is not None:
        issues.append(vendor_vat)
    customer_vat = _vat_issue(
        invoice.customer_vat_id,
        required=False,
        missing_code="customer_vat_id_required",
        invalid_code="customer_vat_id_invalid",
        label="Customer",
    )
    if customer_vat is not None:
        issues.append(customer_vat)
    totals = _totals_issue(
        invoice.subtotal,
        invoice.total_tax,
        invoice.invoice_total,
        "invoice_total_mismatch",
    )
    if totals is not None:
        issues.append(totals)
    return issues


def validate_receipt(receipt: Receipt) -> list[ValidationIssue]:
    totals = _totals_issue(
        receipt.subtotal,
        receipt.total_tax,
        receipt.total,
        "total_mismatch",
    )
    return [totals] if totals is not None else []
