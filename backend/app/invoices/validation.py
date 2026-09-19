from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel
from stdnum.eu import vat

from app.accounting.northstar import NORTHSTAR_CUSTOMER_VAT_ID
from app.invoices.duplicate import DuplicateRegistry, InvoiceKey
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt

TOTAL_TOLERANCE = Decimal("0.01")
LOW_CONFIDENCE_THRESHOLD = 0.80


class IssueSeverity(StrEnum):
    error = "error"
    warning = "warning"


class ValidationIssue(BaseModel):
    code: str
    message: str
    severity: IssueSeverity = IssueSeverity.error


def _required(value: object | None, code: str, message: str) -> ValidationIssue | None:
    if value is None:
        return ValidationIssue(code=code, message=message)
    if isinstance(value, str) and not value.strip():
        return ValidationIssue(code=code, message=message)
    return None


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


def _low_confidence_issue(confidence: float | None) -> ValidationIssue | None:
    if confidence is None or confidence >= LOW_CONFIDENCE_THRESHOLD:
        return None
    return ValidationIssue(
        code="low_extraction_confidence",
        message=(
            f"Primary extraction confidence {confidence:.2f} "
            f"is below {LOW_CONFIDENCE_THRESHOLD:.2f}"
        ),
        severity=IssueSeverity.warning,
    )


def _append(issues: list[ValidationIssue], issue: ValidationIssue | None) -> None:
    if issue is not None:
        issues.append(issue)


def validate_invoice(
    invoice: Invoice,
    *,
    duplicate_registry: DuplicateRegistry | None = None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    _append(
        issues,
        _required(invoice.vendor_name, "vendor_name_required", "Vendor name is required"),
    )
    _append(
        issues,
        _required(
            invoice.customer_name, "customer_name_required", "Customer name is required"
        ),
    )
    _append(
        issues,
        _required(
            invoice.invoice_number, "invoice_number_required", "Invoice number is required"
        ),
    )
    _append(
        issues,
        _required(invoice.invoice_date, "invoice_date_required", "Invoice date is required"),
    )
    _append(
        issues,
        _required(invoice.currency, "currency_required", "Currency is required"),
    )
    _append(
        issues,
        _required(invoice.invoice_total, "invoice_total_required", "Invoice total is required"),
    )
    if invoice.invoice_total is not None and invoice.invoice_total <= 0:
        issues.append(
            ValidationIssue(
                code="invoice_total_not_positive",
                message="Invoice total must be greater than zero",
            )
        )

    _append(
        issues,
        _vat_issue(
            invoice.vendor_vat_id,
            required=True,
            missing_code="vendor_vat_id_required",
            invalid_code="vendor_vat_id_invalid",
            label="Vendor",
        ),
    )
    customer_vat = _vat_issue(
        invoice.customer_vat_id,
        required=False,
        missing_code="customer_vat_id_required",
        invalid_code="customer_vat_id_invalid",
        label="Customer",
    )
    _append(issues, customer_vat)
    if (
        customer_vat is None
        and invoice.customer_vat_id
        and invoice.customer_vat_id.strip() != NORTHSTAR_CUSTOMER_VAT_ID
    ):
        issues.append(
            ValidationIssue(
                code="customer_vat_id_mismatch",
                message="Customer VAT ID does not match Northstar Facilities",
            )
        )

    if (
        invoice.invoice_date is not None
        and invoice.due_date is not None
        and invoice.due_date < invoice.invoice_date
    ):
        issues.append(
            ValidationIssue(
                code="invalid_date_order",
                message="Due date is before invoice date",
            )
        )

    if invoice.purchase_order is None or not invoice.purchase_order.strip():
        issues.append(
            ValidationIssue(
                code="purchase_order_missing",
                message="Purchase order is missing",
                severity=IssueSeverity.warning,
            )
        )

    _append(
        issues,
        _totals_issue(
            invoice.subtotal,
            invoice.total_tax,
            invoice.invoice_total,
            "invoice_total_mismatch",
        ),
    )

    if (
        duplicate_registry is not None
        and invoice.vendor_name
        and invoice.invoice_number
        and duplicate_registry.is_registered(
            InvoiceKey(invoice.vendor_name, invoice.invoice_number)
        )
    ):
        issues.append(
            ValidationIssue(
                code="duplicate_invoice",
                message="An invoice with this vendor and invoice number already exists",
            )
        )

    _append(issues, _low_confidence_issue(invoice.confidence))
    return issues


def validate_receipt(receipt: Receipt) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    _append(
        issues,
        _required(
            receipt.merchant_name, "merchant_name_required", "Merchant name is required"
        ),
    )
    _append(
        issues,
        _required(
            receipt.transaction_date,
            "transaction_date_required",
            "Transaction date is required",
        ),
    )
    _append(
        issues,
        _required(receipt.currency, "currency_required", "Currency is required"),
    )
    _append(
        issues,
        _required(receipt.total, "total_required", "Receipt total is required"),
    )
    if receipt.total is not None and receipt.total <= 0:
        issues.append(
            ValidationIssue(
                code="total_not_positive",
                message="Receipt total must be greater than zero",
            )
        )
    _append(
        issues,
        _required(receipt.total_tax, "total_tax_required", "VAT total is required"),
    )
    _append(
        issues,
        _totals_issue(
            receipt.subtotal,
            receipt.total_tax,
            receipt.total,
            "total_mismatch",
        ),
    )
    _append(issues, _low_confidence_issue(receipt.confidence))
    return issues
