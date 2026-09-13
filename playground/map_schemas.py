"""Map Document Intelligence output onto Invoice and Receipt schemas.

Reuses cached AnalyzeResult JSON when present so repeat runs do not
spend extra Azure pages. Delete files under output/ to force a live call.

Run from this folder:

    uv run --project ../backend --locked --no-sync python map_schemas.py
"""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping
from decimal import Decimal
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
SAMPLES = REPO_ROOT / "samples" / "generated"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
MANIFEST_PATH = REPO_ROOT / "samples" / "manifest.json"

sys.path.insert(0, str(BACKEND_ROOT))

from app.providers.azure_document_intelligence import (  # noqa: E402
    INVOICE_MODEL,
    RECEIPT_MODEL,
    AzureDocumentIntelligenceProvider,
)
from app.schemas.invoice.mapping import (  # noqa: E402
    from_analyze_result as invoice_from_analyze_result,
)
from app.schemas.receipt.mapping import (  # noqa: E402
    from_analyze_result as receipt_from_analyze_result,
)

INVOICE_SAMPLE = SAMPLES / "01-en-happy-classic.pdf"
MISSING_VAT_SAMPLE = SAMPLES / "05-nl-missing-vendor-vat.pdf"
RECEIPT_SAMPLE = SAMPLES / "13-nl-fuel-receipt.png"


def load_manifest() -> dict[str, dict[str, Any]]:
    entries = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {entry["filename"]: entry["expected"] for entry in entries}


def write_json(payload: Mapping[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def load_or_analyze(
    sample_path: Path,
    provider: AzureDocumentIntelligenceProvider,
    model_id: str,
) -> dict[str, Any]:
    cache_path = OUTPUT_DIR / f"{sample_path.stem}.json"
    if cache_path.is_file():
        print(f"Using cached AnalyzeResult: {cache_path.name}")
        return json.loads(cache_path.read_text(encoding="utf-8"))

    print(f"Analyzing {sample_path.name} (live Document Intelligence call)")
    payload = provider.analyze(sample_path, model_id)
    write_json(payload, cache_path)
    return payload


def as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return str(value)


def compare(label: str, mapped: dict[str, Any], expected: dict[str, Any]) -> None:
    print(f"\n{label} vs manifest")
    for key, expected_value in expected.items():
        if key not in mapped:
            continue
        actual = as_text(mapped[key])
        marker = "ok" if actual == expected_value else "DIFF"
        print(f"  [{marker}] {key}: mapped={actual!r} expected={expected_value!r}")


def main() -> None:
    expected = load_manifest()
    provider = AzureDocumentIntelligenceProvider()

    invoice_payload = load_or_analyze(INVOICE_SAMPLE, provider, INVOICE_MODEL)
    invoice = invoice_from_analyze_result(invoice_payload)
    write_json(invoice.model_dump(mode="json"), OUTPUT_DIR / f"{INVOICE_SAMPLE.stem}.invoice.json")
    print("\nInvoice", INVOICE_SAMPLE.name)
    print(invoice.model_dump_json(indent=2))
    compare(
        INVOICE_SAMPLE.name,
        invoice.model_dump(mode="json"),
        expected[INVOICE_SAMPLE.name],
    )

    missing_vat_payload = load_or_analyze(MISSING_VAT_SAMPLE, provider, INVOICE_MODEL)
    missing_vat = invoice_from_analyze_result(missing_vat_payload)
    write_json(
        missing_vat.model_dump(mode="json"),
        OUTPUT_DIR / f"{MISSING_VAT_SAMPLE.stem}.invoice.json",
    )
    print("\nInvoice", MISSING_VAT_SAMPLE.name)
    print(missing_vat.model_dump_json(indent=2))
    compare(
        MISSING_VAT_SAMPLE.name,
        missing_vat.model_dump(mode="json"),
        expected[MISSING_VAT_SAMPLE.name],
    )

    receipt_payload = load_or_analyze(RECEIPT_SAMPLE, provider, RECEIPT_MODEL)
    receipt = receipt_from_analyze_result(receipt_payload)
    write_json(receipt.model_dump(mode="json"), OUTPUT_DIR / f"{RECEIPT_SAMPLE.stem}.receipt.json")
    print("\nReceipt", RECEIPT_SAMPLE.name)
    print(receipt.model_dump_json(indent=2))
    receipt_expected = expected[RECEIPT_SAMPLE.name]
    compare(
        RECEIPT_SAMPLE.name,
        {
            "vendor_name": receipt.merchant_name,
            "invoice_date": as_text(receipt.transaction_date),
            "currency": receipt.currency,
            "subtotal": receipt.subtotal,
            "total_tax": receipt.total_tax,
            "invoice_total": receipt.total,
        },
        receipt_expected,
    )


if __name__ == "__main__":
    main()
