from __future__ import annotations

import logging
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from pydantic_ai import Agent, BinaryContent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.azure import AzureProvider

from app.config import Settings

if TYPE_CHECKING:
    from app.pipeline.base import PipelineContext

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = (
    "Classify this financial document as invoice or receipt based on its layout and content."
)

CLASSIFICATION_INSTRUCTIONS = """\
You classify European financial documents for a finance team.

Choose invoice when the document is a supplier bill requesting payment. Invoices usually
include an invoice number, supplier and customer details, VAT IDs, line items, totals,
and often a due date or payment terms.

Choose receipt when the document records an expense that was already paid. Receipts usually
show a merchant, transaction date, payment total, and sometimes VAT, but not invoice
numbers, customer VAT IDs, purchase orders, or payment terms.

Return your best label, a confidence between 0 and 1, and a brief reason.
"""

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class DocumentKind(StrEnum):
    invoice = "invoice"
    receipt = "receipt"


class DocumentClassification(BaseModel):
    document_kind: DocumentKind
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class DocumentClassifier:
    """Classify a PDF or image as invoice or receipt via Azure OpenAI."""

    def __init__(self, settings: Settings | None = None) -> None:
        resolved_settings = settings or Settings()
        provider = AzureProvider(
            azure_endpoint=resolved_settings.azure_openai_endpoint,
            api_key=resolved_settings.azure_openai_api_key,
        )
        model = OpenAIResponsesModel(
            model_name=resolved_settings.azure_openai_deployment,
            provider=provider,
        )
        self._agent: Agent[None, DocumentClassification] = Agent(
            model=model,
            output_type=DocumentClassification,
            instructions=CLASSIFICATION_INSTRUCTIONS,
        )

    def run(self, document_path: Path) -> DocumentClassification:
        media_type = MEDIA_TYPES.get(document_path.suffix.lower())
        if media_type is None:
            supported = ", ".join(sorted(MEDIA_TYPES))
            raise ValueError(
                f"Unsupported document type {document_path.suffix!r}. Use one of: {supported}"
            )

        result = self._agent.run_sync(
            user_prompt=[
                CLASSIFICATION_PROMPT,
                BinaryContent(
                    data=document_path.read_bytes(),
                    media_type=media_type,
                ),
            ]
        )
        return result.output


class ClassificationStep:
    """Pipeline step that classifies the document and writes ctx.classification."""

    name = "classification"

    def __init__(self, classifier: DocumentClassifier | None = None) -> None:
        self._classifier = classifier or DocumentClassifier()

    def run(self, ctx: PipelineContext) -> PipelineContext:
        logger.info("Classifying document with Azure OpenAI")
        classification = self._classifier.run(ctx.document_path)
        logger.info(
            "Classified as %s (confidence=%.2f)",
            classification.document_kind,
            classification.confidence,
        )
        return ctx.model_copy(update={"classification": classification})
