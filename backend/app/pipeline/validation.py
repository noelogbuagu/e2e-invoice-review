from __future__ import annotations

import logging
from typing import assert_never

from app.invoices.duplicate import DuplicateRegistry
from app.invoices.validation import validate_invoice, validate_receipt
from app.pipeline.base import DocumentKind, PipelineContext, ValidationState

logger = logging.getLogger(__name__)


class ValidationStep:
    """Run Plurobi invoice or receipt policy on the extracted document."""

    name = "validation"

    def __init__(self, duplicate_registry: DuplicateRegistry | None = None) -> None:
        self._duplicate_registry = duplicate_registry

    def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.classification is None:
            raise ValueError("Validation requires classification")
        if ctx.extraction is None:
            raise ValueError("Validation requires extraction")

        kind = ctx.classification.document_kind
        if kind is DocumentKind.invoice:
            if ctx.extraction.invoice is None:
                raise ValueError("Validation requires an extracted invoice")
            issues = validate_invoice(
                ctx.extraction.invoice,
                duplicate_registry=self._duplicate_registry,
            )
        elif kind is DocumentKind.receipt:
            if ctx.extraction.receipt is None:
                raise ValueError("Validation requires an extracted receipt")
            issues = validate_receipt(ctx.extraction.receipt)
        else:
            assert_never(kind)

        if not issues:
            logger.info("0 issues")
        else:
            codes = ", ".join(issue.code for issue in issues)
            logger.info("%s issue%s: %s", len(issues), "" if len(issues) == 1 else "s", codes)
        return ctx.model_copy(update={"validation": ValidationState(issues=issues)})
