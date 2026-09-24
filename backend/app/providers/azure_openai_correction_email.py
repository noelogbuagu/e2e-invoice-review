"""Correction-email drafting through Azure OpenAI. The app never sends the result."""

from __future__ import annotations

import json

from pydantic_ai import Agent

from app.config import Settings
from app.correction_email.base import CorrectionEmailDraftingError
from app.correction_email.schemas import CorrectionEmailContent
from app.invoices.validation import ValidationIssue
from app.providers.azure_openai import build_responses_model
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt

DRAFT_INSTRUCTIONS = """\
Draft a concise, professional correction-request email from a finance administrator to the
supplier or merchant named in the document. Mention only the listed validation issues and the
document facts you are given (invoice number, dates, amounts, VAT numbers). Ask for a corrected
document or a clarification. Do not mention AI, extraction confidence, internal systems, or
other suppliers, and do not invent an email address or contact person. Use a neutral greeting
and sign off as Maya, Finance Administration, Plurobi
"""


class AzureOpenAICorrectionEmailDrafter:
    def __init__(self, settings: Settings | None = None) -> None:
        self._agent: Agent[None, CorrectionEmailContent] = Agent(
            model=build_responses_model(settings),
            output_type=CorrectionEmailContent,
            instructions=DRAFT_INSTRUCTIONS,
        )

    def draft(
        self, document: Invoice | Receipt, issues: list[ValidationIssue]
    ) -> CorrectionEmailContent:
        payload = {
            "document": document.model_dump(mode="json", exclude={"items", "confidence"}),
            "issues": [issue.model_dump(mode="json") for issue in issues],
        }
        try:
            result = self._agent.run_sync(user_prompt=json.dumps(payload))
        except Exception as error:
            raise CorrectionEmailDraftingError(
                "Azure OpenAI could not draft the correction email."
            ) from error
        return result.output
