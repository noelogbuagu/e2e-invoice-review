from __future__ import annotations

import logging
from typing import assert_never

from app.invoices.validation import validate_invoice, validate_receipt
from app.pipeline.base import DocumentKind, PipelineContext

logger = logging.getLogger(__name__)


class ValidationStep:
    """Run VAT and totals checks on the extracted invoice or receipt."""

    name = "validation"

    def run(self, ctx: PipelineContext) -> PipelineContext:
        if ctx.classification is None:
            raise ValueError("Validation requires classification")

        kind = ctx.classification.document_kind
        if kind is DocumentKind.invoice:
            if ctx.invoice is None:
                raise ValueError("Validation requires an extracted invoice")
            issues = validate_invoice(ctx.invoice)
        elif kind is DocumentKind.receipt:
            if ctx.receipt is None:
                raise ValueError("Validation requires an extracted receipt")
            issues = validate_receipt(ctx.receipt)
        else:
            assert_never(kind)

        if not issues:
            logger.info("0 issues")
        else:
            codes = ", ".join(issue.code for issue in issues)
            logger.info("%s issue%s: %s", len(issues), "" if len(issues) == 1 else "s", codes)
        return ctx.model_copy(update={"issues": issues})
