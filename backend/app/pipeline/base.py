from __future__ import annotations

import logging
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, Field

from app.invoices.validation import ValidationIssue
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt

logger = logging.getLogger(__name__)


class DocumentKind(StrEnum):
    invoice = "invoice"
    receipt = "receipt"


class DocumentClassification(BaseModel):
    document_kind: DocumentKind
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class PipelineContext(BaseModel):
    document_path: Path
    classification: DocumentClassification | None = None
    invoice: Invoice | None = None
    receipt: Receipt | None = None
    issues: list[ValidationIssue] = Field(default_factory=list)


class PipelineStep(Protocol):
    name: str

    def run(self, ctx: PipelineContext) -> PipelineContext: ...


class Pipeline:
    """Run pipeline steps in order, logging each step for audit."""

    def __init__(self, steps: Sequence[PipelineStep]) -> None:
        self._steps = list(steps)

    def run(self, ctx: PipelineContext) -> PipelineContext:
        logger.info("pipeline starting (%s)", ctx.document_path.name)
        for step in self._steps:
            logger.info("starting %s", step.name)
            ctx = step.run(ctx)
            logger.info("finished %s", step.name)
        logger.info("pipeline complete")
        return ctx
