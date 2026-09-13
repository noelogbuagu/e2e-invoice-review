"""Inspect Document Intelligence output for a sample invoice.

Run from this folder:

    uv run --project ../backend --locked --no-sync python inspect_invoice.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
SAMPLE_INVOICE = REPO_ROOT / "samples" / "generated" / "01-en-happy-classic.pdf"
OUTPUT_PATH = Path(__file__).resolve().parent / "output" / f"{SAMPLE_INVOICE.stem}.json"

sys.path.insert(0, str(BACKEND_ROOT))

from app.providers.azure_document_intelligence import (  # noqa: E402
    INVOICE_MODEL,
    AzureDocumentIntelligenceProvider,
)


def write_result(payload: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def field_preview(field: dict[str, object]) -> str:
    if field.get("type") == "array":
        items = field.get("valueArray") or []
        return f"{len(items)} items" if isinstance(items, list) else "array"
    content = field.get("content")
    return str(content) if content is not None else "-"


def print_field_summary(payload: dict[str, object]) -> None:
    documents = payload.get("documents")
    if not isinstance(documents, list) or not documents:
        print("No documents in AnalyzeResult.")
        return

    first_document = documents[0]
    fields = first_document.get("fields", {}) if isinstance(first_document, dict) else {}
    if not isinstance(fields, dict):
        print("No fields in AnalyzeResult.")
        return

    print(f"modelId: {payload.get('modelId')}")
    print(f"apiVersion: {payload.get('apiVersion')}")
    print(f"fields: {len(fields)}")
    print()
    for name, field in fields.items():
        if not isinstance(field, dict):
            continue
        print(f"{name}: {field_preview(field)} ({field.get('confidence')})")


def main() -> None:
    provider = AzureDocumentIntelligenceProvider()
    payload = provider.analyze(SAMPLE_INVOICE, INVOICE_MODEL)

    write_result(payload, OUTPUT_PATH)
    print_field_summary(payload)
    print()
    print(f"Full AnalyzeResult written to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
