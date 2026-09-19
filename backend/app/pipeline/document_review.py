from __future__ import annotations

import logging

from app.document_review.base import DocumentReviewer, DocumentReviewError
from app.document_review.reconciliation import merge_document, primary_field_sources
from app.document_review.schemas import DocumentReview
from app.pipeline.base import ExtractionState, PipelineContext
from app.providers.azure_openai_document_review import AzureOpenAIDocumentReviewer

logger = logging.getLogger(__name__)


class DocumentReviewStep:
    """Second look at the original file; Document Intelligence stays primary."""

    name = "document_review"

    def __init__(self, reviewer: DocumentReviewer | None = None) -> None:
        self._reviewer = reviewer or AzureOpenAIDocumentReviewer()

    def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.extraction is None:
            raise ValueError("Document review requires extraction")
        document = ctx.extraction.invoice or ctx.extraction.receipt
        if document is None:
            raise ValueError("Document review requires an extracted invoice or receipt")

        primary_only = ctx.extraction.model_copy(
            update={"field_sources": primary_field_sources(document)}
        )
        try:
            secondary = self._reviewer.review(ctx.document_path)
        except DocumentReviewError as error:
            logger.warning("independent review unavailable: %s", error)
            return ctx.model_copy(
                update={
                    "extraction": primary_only,
                    "document_review": DocumentReview(error_message=str(error)),
                }
            )

        if secondary.document_kind == "unsupported":
            logger.warning("independent review did not recognise an invoice or receipt")
            return ctx.model_copy(
                update={
                    "extraction": primary_only,
                    "document_review": DocumentReview(
                        extraction=secondary,
                        error_message=(
                            "The independent reviewer did not recognise this file as an "
                            "invoice or receipt, so only Document Intelligence values are used."
                        ),
                    ),
                }
            )

        merged, field_sources, review = merge_document(document, secondary)
        extraction = ExtractionState(field_sources=field_sources)
        if ctx.extraction.invoice is not None:
            extraction.invoice = merged
        else:
            extraction.receipt = merged
        conflicts = sum(item.status == "different" for item in review.comparisons)
        logger.info(
            "merged %s fallback field(s), %s conflict(s) kept on Document Intelligence",
            len(review.fallback_fields),
            conflicts,
        )
        return ctx.model_copy(update={"extraction": extraction, "document_review": review})
