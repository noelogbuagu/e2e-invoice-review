from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.accounting.catalog import GlAccountSuggestion
from app.pipeline.base import DocumentClassification, ExtractionState, ValidationState

DocumentStatus = Literal["processing", "ready", "needs_review", "failed"]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_filename: str
    content_type: str
    status: DocumentStatus
    classification: DocumentClassification | None = None
    extraction: ExtractionState | None = None
    validation: ValidationState | None = None
    gl_suggestion: GlAccountSuggestion | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
