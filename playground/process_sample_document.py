"""Classify, extract, LLM-review, validate, and suggest a GL account for a sample document.

Edit DOCUMENT_PATH below, then run main() in the interactive window.
Terminal: uv run --project ../backend --locked --no-sync python process_sample_document.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str((REPO_ROOT := Path(__file__).resolve().parents[1]) / "backend"))
sys.path.append(str(Path(__file__).resolve().parent))

import bootstrap  # noqa: F401
from bootstrap import SAMPLES

from app.invoices.duplicate import InMemoryDuplicateRegistry, InvoiceKey
from app.pipeline import PipelineContext, build_document_pipeline

DOCUMENT_PATH = SAMPLES / "01-en-happy-classic.pdf"
# DOCUMENT_PATH = SAMPLES / "05-nl-missing-vendor-vat.pdf"
# DOCUMENT_PATH = SAMPLES / "06-de-invalid-vendor-vat.pdf"
# DOCUMENT_PATH = SAMPLES / "08-en-total-mismatch.pdf"
# DOCUMENT_PATH = SAMPLES / "09-nl-missing-po.pdf"
# DOCUMENT_PATH = SAMPLES / "10-de-duplicate.pdf"
# DOCUMENT_PATH = SAMPLES / "13-nl-fuel-receipt.png"

SEED_DUPLICATE_FOR_DEMO = False


def _duplicate_registry() -> InMemoryDuplicateRegistry | None:
    if not SEED_DUPLICATE_FOR_DEMO and DOCUMENT_PATH.name != "10-de-duplicate.pdf":
        return None
    registry = InMemoryDuplicateRegistry()
    registry.register(InvoiceKey("Rhein Wartung GmbH", "DE-2026-3098"))
    return registry


def main() -> None:
    ctx = build_document_pipeline(duplicate_registry=_duplicate_registry()).run(
        PipelineContext(document_path=DOCUMENT_PATH)
    )
    if ctx.classification is not None:
        print(ctx.classification.model_dump_json(indent=2))
    if ctx.extraction is not None:
        print(ctx.extraction.model_dump_json(indent=2))
    if ctx.document_review is not None:
        print(ctx.document_review.model_dump_json(indent=2))
    if ctx.validation is not None:
        print(ctx.validation.model_dump_json(indent=2))
    if ctx.gl_suggestion is not None:
        print(ctx.gl_suggestion.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
