"""Classify a sample document as invoice or receipt.

Edit DOCUMENT_PATH below, then run main() in the interactive window.
Terminal: uv run --project ../backend --locked --no-sync python classify_sample_document.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str((REPO_ROOT := Path(__file__).resolve().parents[1]) / "backend"))
sys.path.append(str(Path(__file__).resolve().parent))

import bootstrap  # noqa: F401
from bootstrap import SAMPLES

from app.pipeline.classification import DocumentClassifier

DOCUMENT_PATH = SAMPLES / "01-en-happy-classic.pdf"
# DOCUMENT_PATH = SAMPLES / "13-nl-fuel-receipt.png"


def main() -> None:
    classification = DocumentClassifier().run(DOCUMENT_PATH)
    print(classification.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
