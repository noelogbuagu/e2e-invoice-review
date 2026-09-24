"""Run Document Intelligence + Plurobi policy over the fictional corpus against the manifest.

Run from backend/: uv run --locked --no-sync python -m scripts.evaluate_corpus
Cost: one Document Intelligence analyze per sample (14 pages for the 13 files). No OpenAI calls.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.invoices.validation import validate_invoice, validate_receipt
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt
from app.services.document_intelligence_service import DocumentIntelligenceService

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "samples" / "manifest.json"
SAMPLES = ROOT / "samples" / "generated"

DECIMAL_FIELDS = {"subtotal", "total_tax", "invoice_total"}
DATE_FIELDS = {"invoice_date", "due_date"}
IDENTIFIER_FIELDS = {"vendor_vat_id", "customer_vat_id", "invoice_number", "purchase_order"}
# The manifest uses invoice-shaped keys for every sample; receipts map onto them.
RECEIPT_ALIASES = {
    "vendor_name": "merchant_name",
    "invoice_date": "transaction_date",
    "invoice_total": "total",
}


def _normalized_text(value: Any) -> str:
    return " ".join(str(value).casefold().split())


def _normalized_identifier(value: Any) -> str:
    """VAT IDs and numbers may be printed with spaces or dashes; stdnum ignores them too."""
    return "".join(character for character in str(value).upper() if character.isalnum())


def _equal(field: str, expected: Any, actual: Any) -> bool:
    if expected is None:
        return actual is None
    if actual is None:
        return False
    if field in DECIMAL_FIELDS:
        try:
            return Decimal(str(expected)) == Decimal(str(actual))
        except InvalidOperation:
            return False
    if field in DATE_FIELDS:
        return str(expected) == (actual.isoformat() if isinstance(actual, date) else str(actual))
    if field in IDENTIFIER_FIELDS:
        return _normalized_identifier(expected) == _normalized_identifier(actual)
    return _normalized_text(expected) == _normalized_text(actual)


def _actual_value(document: Invoice | Receipt, field: str, document_type: str) -> Any:
    if field == "document_type":
        return document_type
    if isinstance(document, Receipt):
        field = RECEIPT_ALIASES.get(field, field)
    return getattr(document, field, None)


def compare_fields(
    expected: Mapping[str, Any], document: Invoice | Receipt, document_type: str
) -> dict[str, bool]:
    return {
        field: _equal(field, value, _actual_value(document, field, document_type))
        for field, value in expected.items()
    }


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    service = DocumentIntelligenceService()

    matched_fields = total_fields = exact_documents = policy_matches = failures = 0

    print(f"Evaluating {len(manifest)} fictional financial documents\n")
    for entry in manifest:
        filename = entry["filename"]
        document_type = entry.get("document_type", "invoice")
        try:
            path = SAMPLES / filename
            document: Invoice | Receipt = (
                service.analyze_receipt(path)
                if document_type == "receipt"
                else service.analyze_invoice(path)
            )
        except Exception as error:  # noqa: BLE001 - keep evaluating the remaining files
            failures += 1
            print(f"FAIL  {filename:<32} provider error: {error}")
            continue

        comparison = compare_fields(entry["expected"], document, document_type)
        issues = (
            validate_receipt(document)
            if isinstance(document, Receipt)
            else validate_invoice(document)
        )
        issue_codes = sorted(issue.code for issue in issues)
        expected_codes = sorted(entry.get("expected_issue_codes", []))
        # Duplicate detection needs a stored peer; this offline run accepts no issues for 10.
        policy_ok = issue_codes == expected_codes or (
            expected_codes == ["duplicate_invoice"] and issue_codes == []
        )

        mismatches = [field for field, ok in comparison.items() if not ok]
        matched_fields += sum(comparison.values())
        total_fields += len(comparison)
        exact_documents += not mismatches
        policy_matches += policy_ok
        result = "PASS" if not mismatches else "PART"
        detail = "all fields" if not mismatches else f"mismatch: {', '.join(mismatches)}"
        policy = "policy-ok" if policy_ok else f"policy={issue_codes} expected={expected_codes}"
        print(
            f"{result}  {filename:<32} {sum(comparison.values()):>2}/{len(comparison)}  "
            f"{detail}  {policy}"
        )

    accuracy = (matched_fields / total_fields * 100) if total_fields else 0
    print("\nSummary")
    print(f"  Field accuracy:    {matched_fields}/{total_fields} ({accuracy:.1f}%)")
    print(f"  Exact documents:   {exact_documents}/{len(manifest)}")
    print(f"  Policy matches:    {policy_matches}/{len(manifest)}")
    print(f"  Provider failures: {failures}/{len(manifest)}")


if __name__ == "__main__":
    main()
