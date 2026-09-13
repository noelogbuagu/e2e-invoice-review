"""Inspect Document Intelligence output for a sample invoice.

Edit DOCUMENT_PATH below, then run main() in the interactive window.
Terminal: uv run --project ../backend --locked --no-sync python analyse_sample_invoice.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))

import bootstrap  # noqa: F401
from bootstrap import OUTPUT_DIR, SAMPLES

from app.providers.azure_document_intelligence import (
    INVOICE_MODEL,
    AzureDocumentIntelligenceProvider,
)

DOCUMENT_PATH = SAMPLES / "01-en-happy-classic.pdf"
# DOCUMENT_PATH = SAMPLES / "05-nl-missing-vendor-vat.pdf"


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
    output_path = OUTPUT_DIR / f"{DOCUMENT_PATH.stem}.json"
    payload = AzureDocumentIntelligenceProvider().analyze(DOCUMENT_PATH, INVOICE_MODEL)

    write_result(payload, output_path)
    print_field_summary(payload)
    print()
    print(f"Analyzed {DOCUMENT_PATH}")
    print(f"Full AnalyzeResult written to {output_path}")


if __name__ == "__main__":
    main()
