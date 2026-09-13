"""Inspect Document Intelligence output for a sample invoice.

Run from this folder. Pass a document path to analyze a different sample:

    uv run --project ../backend --locked --no-sync python inspect_invoice.py
    uv run --project ../backend --locked --no-sync python inspect_invoice.py ../samples/generated/05-nl-missing-vendor-vat.pdf
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
SAMPLES = REPO_ROOT / "samples" / "generated"
DEFAULT_SAMPLE = SAMPLES / "01-en-happy-classic.pdf"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"

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


def resolve_sample(args: list[str]) -> Path:
    if not args:
        return DEFAULT_SAMPLE

    candidate = Path(args[0])
    if not candidate.is_file():
        candidate = REPO_ROOT / args[0]
    if not candidate.is_file():
        candidate = SAMPLES / args[0]
    if not candidate.is_file():
        raise FileNotFoundError(f"Document not found: {args[0]}")
    return candidate


def main() -> None:
    sample = resolve_sample(sys.argv[1:])
    output_path = OUTPUT_DIR / f"{sample.stem}.json"
    provider = AzureDocumentIntelligenceProvider()
    payload = provider.analyze(sample, INVOICE_MODEL)

    write_result(payload, output_path)
    print_field_summary(payload)
    print()
    print(f"Analyzed {sample}")
    print(f"Full AnalyzeResult written to {output_path}")


if __name__ == "__main__":
    main()
