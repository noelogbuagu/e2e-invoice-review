from __future__ import annotations

import logging
from typing import assert_never

from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIResponsesModel
from pydantic_ai.providers.azure import AzureProvider

from app.accounting.catalog import GlAccountCode, GlAccountSuggestion
from app.accounting.selection import catalog_text, resolve_account
from app.config import Settings, get_settings
from app.pipeline.base import DocumentKind, PipelineContext
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt

logger = logging.getLogger(__name__)


class _GlPick(BaseModel):
    account_code: GlAccountCode
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


GL_SUGGESTION_INSTRUCTIONS = f"""\
You assign a Northstar Facilities general-ledger account to an extracted invoice or receipt.

Choose exactly one account code from this catalog:

{catalog_text()}

Base the choice on evidence in the document text: line-item descriptions and
receipt expense category first, then vendor or merchant name. When text and name
conflict, follow the catalog account whose description best matches the text.
Lower confidence when the match is weak or ambiguous.
Return the account code, a confidence between 0 and 1, and a brief reason.
The suggestion is a hint for a human reviewer, who may override it.
"""


class GlAccountSuggester:
    """Suggest a Northstar GL account from normalized invoice or receipt fields."""

    def __init__(self, settings: Settings | None = None) -> None:
        resolved_settings = settings or get_settings()
        provider = AzureProvider(
            azure_endpoint=resolved_settings.azure_openai_endpoint,
            api_key=resolved_settings.azure_openai_api_key,
        )
        model = OpenAIResponsesModel(
            model_name=resolved_settings.azure_openai_deployment,
            provider=provider,
        )
        self._agent: Agent[None, _GlPick] = Agent(
            model=model,
            output_type=_GlPick,
            instructions=GL_SUGGESTION_INSTRUCTIONS,
        )

    def suggest(self, document: Invoice | Receipt) -> GlAccountSuggestion:
        pick = self._agent.run_sync(user_prompt=document.model_dump_json()).output
        account = resolve_account(pick.account_code)
        return GlAccountSuggestion(
            account_code=account.code,
            account_name=account.name,
            confidence=pick.confidence,
            reasoning=pick.reasoning,
        )


class GlSuggestionStep:
    """Pipeline step that suggests a GL account from extracted invoice or receipt fields."""

    name = "gl_suggestion"

    def __init__(self, suggester: GlAccountSuggester | None = None) -> None:
        self._suggester = suggester or GlAccountSuggester()

    def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.classification is None:
            raise ValueError("GL suggestion requires classification")
        if ctx.extraction is None:
            raise ValueError("GL suggestion requires extraction")

        kind = ctx.classification.document_kind
        if kind is DocumentKind.invoice:
            if ctx.extraction.invoice is None:
                raise ValueError("GL suggestion requires an extracted invoice")
            document: Invoice | Receipt = ctx.extraction.invoice
        elif kind is DocumentKind.receipt:
            if ctx.extraction.receipt is None:
                raise ValueError("GL suggestion requires an extracted receipt")
            document = ctx.extraction.receipt
        else:
            assert_never(kind)

        suggestion = self._suggester.suggest(document)
        logger.info(
            "suggested GL %s %s (confidence=%.2f)",
            suggestion.account_code,
            suggestion.account_name,
            suggestion.confidence,
        )
        return ctx.model_copy(update={"gl_suggestion": suggestion})
