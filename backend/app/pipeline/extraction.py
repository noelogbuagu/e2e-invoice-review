from __future__ import annotations

import logging
from typing import assert_never

from app.pipeline.base import DocumentKind, PipelineContext
from app.providers.azure_document_intelligence import INVOICE_MODEL, RECEIPT_MODEL
from app.services.document_intelligence_service import DocumentIntelligenceService

logger = logging.getLogger(__name__)


class ExtractionStep:
    """Extract invoice or receipt fields with the matching Document Intelligence model."""

    name = "extraction"

    def __init__(self, service: DocumentIntelligenceService | None = None) -> None:
        self._service = service or DocumentIntelligenceService()

    def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.classification is None:
            raise ValueError("Extraction requires classification")

        kind = ctx.classification.document_kind
        if kind is DocumentKind.invoice:
            logger.info("extracting with %s", INVOICE_MODEL)
            invoice = self._service.analyze_invoice(ctx.document_path)
            logger.info("mapped %s line items", len(invoice.items))
            return ctx.model_copy(update={"invoice": invoice})
        if kind is DocumentKind.receipt:
            logger.info("extracting with %s", RECEIPT_MODEL)
            receipt = self._service.analyze_receipt(ctx.document_path)
            logger.info("mapped %s line items", len(receipt.items))
            return ctx.model_copy(update={"receipt": receipt})
        assert_never(kind)
