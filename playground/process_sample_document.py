"""Classify, extract, and validate a sample invoice or receipt.

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

from app.pipeline import PipelineContext, build_document_pipeline

DOCUMENT_PATH = SAMPLES / "01-en-happy-classic.pdf"
# DOCUMENT_PATH = SAMPLES / "05-nl-missing-vendor-vat.pdf"
# DOCUMENT_PATH = SAMPLES / "06-de-invalid-vendor-vat.pdf"
# DOCUMENT_PATH = SAMPLES / "08-en-total-mismatch.pdf"
# DOCUMENT_PATH = SAMPLES / "13-nl-fuel-receipt.png"


def main() -> None:
    ctx = build_document_pipeline().run(PipelineContext(document_path=DOCUMENT_PATH))
    if ctx.classification is not None:
        print(ctx.classification.model_dump_json(indent=2))
    if ctx.invoice is not None:
        print(ctx.invoice.model_dump_json(indent=2))
    if ctx.receipt is not None:
        print(ctx.receipt.model_dump_json(indent=2))
    print([issue.model_dump() for issue in ctx.issues])


if __name__ == "__main__":
    main()
