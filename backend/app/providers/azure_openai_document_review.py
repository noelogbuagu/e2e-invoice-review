"""Independent LLM reading of the original PDF or image through Azure OpenAI."""

from __future__ import annotations

from pathlib import Path

from pydantic_ai import Agent, BinaryContent

from app.config import Settings
from app.document_review.base import DocumentReviewError
from app.document_review.schemas import LlmDocumentExtraction
from app.providers.azure_openai import build_responses_model

MEDIA_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}

REVIEW_PROMPT = "Independently read this financial document and return every requested value."

REVIEW_INSTRUCTIONS = """\
You are an independent financial-document reviewer for a European finance team.

Read the source document yourself. You are not given any other extraction and must not
guess what another system produced. First decide whether it is an invoice, a receipt, or
unsupported. Then fill every field directly from what is printed.

For receipts, put the merchant in vendor_name, the transaction date in invoice_date, the
paid total in total, and classify the expense as fuel, meals, travel, supplies, or other in
expense_category. Leave invoice-only fields null for receipts.

Return dates as YYYY-MM-DD, monetary values as plain decimal strings without currency symbols,
VAT IDs exactly as printed, and currency as an ISO code. Use null when a value is absent or
unreadable. Do not correct, reconcile, or judge the document; deterministic rules do that.
The summary is one factual sentence.
"""


class AzureOpenAIDocumentReviewer:
    """Secondary reviewer: sends the original file and returns strict structured fields."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._agent: Agent[None, LlmDocumentExtraction] = Agent(
            model=build_responses_model(settings),
            output_type=LlmDocumentExtraction,
            instructions=REVIEW_INSTRUCTIONS,
        )

    def review(self, document_path: Path) -> LlmDocumentExtraction:
        media_type = MEDIA_TYPES.get(document_path.suffix.lower())
        if media_type is None:
            raise DocumentReviewError(
                f"Unsupported document type {document_path.suffix!r} for the LLM review."
            )
        try:
            result = self._agent.run_sync(
                user_prompt=[
                    REVIEW_PROMPT,
                    BinaryContent(data=document_path.read_bytes(), media_type=media_type),
                ]
            )
        except Exception as error:
            raise DocumentReviewError(
                "Azure OpenAI could not complete the independent document review."
            ) from error
        return result.output
