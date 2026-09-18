from app.pipeline.base import (
    DocumentClassification,
    DocumentKind,
    Pipeline,
    PipelineContext,
)
from app.pipeline.classification import ClassificationStep, DocumentClassifier
from app.pipeline.extraction import ExtractionStep
from app.pipeline.validation import ValidationStep

__all__ = [
    "ClassificationStep",
    "DocumentClassification",
    "DocumentClassifier",
    "DocumentKind",
    "ExtractionStep",
    "Pipeline",
    "PipelineContext",
    "ValidationStep",
    "build_document_pipeline",
]


def build_document_pipeline() -> Pipeline:
    return Pipeline(
        [
            ClassificationStep(),
            ExtractionStep(),
            ValidationStep(),
        ]
    )
