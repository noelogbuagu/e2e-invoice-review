"""Classify a sample document as invoice or receipt.

Run from this folder. Pass a document path to classify a different sample:

    uv run --project ../backend --locked --no-sync python classify_sample_document.py
    uv run --project ../backend --locked --no-sync python classify_sample_document.py ../samples/generated/13-nl-fuel-receipt.png
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_ROOT = REPO_ROOT / "backend"
SAMPLES = REPO_ROOT / "samples" / "generated"
DEFAULT_SAMPLE = SAMPLES / "01-en-happy-classic.pdf"

sys.path.insert(0, str(BACKEND_ROOT))

from app.pipeline.classification import DocumentClassifier  # noqa: E402


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
    classification = DocumentClassifier().run(sample)
    print(classification.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
