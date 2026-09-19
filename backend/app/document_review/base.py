from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.document_review.schemas import LlmDocumentExtraction


class DocumentReviewError(RuntimeError):
    pass


class DocumentReviewer(Protocol):
    def review(self, document_path: Path) -> LlmDocumentExtraction: ...
