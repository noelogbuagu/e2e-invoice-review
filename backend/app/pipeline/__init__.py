from app.accounting.catalog import GlAccountSuggestion
from app.invoices.duplicate import DuplicateRegistry
from app.pipeline.base import (
    DocumentClassification,
    DocumentKind,
    ExtractionState,
    Pipeline,
    PipelineContext,
    ValidationState,
)
from app.pipeline.classification import ClassificationStep, DocumentClassifier
from app.pipeline.document_review import DocumentReviewStep
from app.pipeline.extraction import ExtractionStep
from app.pipeline.gl_suggestion import GlAccountSuggester, GlSuggestionStep
from app.pipeline.validation import ValidationStep

__all__ = [
    "ClassificationStep",
    "DocumentClassification",
    "DocumentClassifier",
    "DocumentKind",
    "DocumentReviewStep",
    "ExtractionState",
    "ExtractionStep",
    "GlAccountSuggester",
    "GlAccountSuggestion",
    "GlSuggestionStep",
    "Pipeline",
    "PipelineContext",
    "ValidationState",
    "ValidationStep",
    "build_document_pipeline",
]


def build_document_pipeline(
    duplicate_registry: DuplicateRegistry | None = None,
) -> Pipeline:
    return Pipeline(
        [
            ClassificationStep(),
            ExtractionStep(),
            DocumentReviewStep(),
            ValidationStep(duplicate_registry=duplicate_registry),
            GlSuggestionStep(),
        ]
    )
