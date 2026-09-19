"""Compare Document Intelligence (primary) with the independent LLM review on chosen samples.

Run from backend/: uv run --locked --no-sync python -m scripts.evaluate_hybrid [filenames...]
Cost per file: one Document Intelligence page and one Azure OpenAI Responses call.
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

from app.document_review.reconciliation import merge_document, primary_field_sources
from app.documents.service import status_for_issues
from app.invoices.validation import validate_invoice, validate_receipt
from app.providers.azure_openai_document_review import AzureOpenAIDocumentReviewer
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt
from app.services.document_intelligence_service import DocumentIntelligenceService

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "samples" / "manifest.json"
SAMPLES = ROOT / "samples" / "generated"
DEFAULT_FILES = ("02-nl-happy-compact.pdf", "13-nl-fuel-receipt.png")


def evaluate(
    filename: str,
    document_type: str,
    service: DocumentIntelligenceService,
    reviewer: AzureOpenAIDocumentReviewer,
) -> dict[str, Any]:
    path = SAMPLES / filename
    primary: Invoice | Receipt = (
        service.analyze_receipt(path)
        if document_type == "receipt"
        else service.analyze_invoice(path)
    )
    merged, _sources, review = merge_document(primary, reviewer.review(path))
    issues = (
        validate_receipt(merged) if isinstance(merged, Receipt) else validate_invoice(merged)
    )

    return {
        "filename": filename,
        "document_type": document_type,
        "llm_document_kind": review.extraction.document_kind if review.extraction else None,
        "primary_fields": sorted(primary_field_sources(primary)),
        "fallback_fields": review.fallback_fields,
        "conflict_fields": [c.field for c in review.comparisons if c.status == "different"],
        "final_status": status_for_issues(issues),
        "issue_codes": [issue.code for issue in issues],
        "model_calls": {"document_intelligence": 1, "azure_openai_review": 1},
    }


def main() -> None:
    logging.basicConfig(level=logging.WARNING)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("filenames", nargs="*", default=list(DEFAULT_FILES))
    args = parser.parse_args()

    manifest = {
        entry["filename"]: entry for entry in json.loads(MANIFEST_PATH.read_text("utf-8"))
    }
    service = DocumentIntelligenceService()
    reviewer = AzureOpenAIDocumentReviewer()

    results = []
    for filename in args.filenames:
        entry = manifest.get(filename)
        if entry is None:
            print(f"SKIP  {filename}: not in samples/manifest.json")
            continue
        try:
            result = evaluate(filename, entry["document_type"], service, reviewer)
        except Exception as error:  # noqa: BLE001 - keep evaluating the remaining files
            print(f"FAIL  {filename}: {error}")
            continue
        expected = sorted(entry.get("expected_issue_codes", []))
        actual = sorted(result["issue_codes"])
        result["policy_ok"] = actual == expected
        results.append(result)
        verdict = "PASS" if result["policy_ok"] else "DIFF"
        print(
            f"{verdict}  {filename:<32} status={result['final_status']} "
            f"fallback={result['fallback_fields']} conflicts={result['conflict_fields']} "
            f"issues={actual} expected={expected}"
        )

    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
