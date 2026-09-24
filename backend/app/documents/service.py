from pathlib import Path
from uuid import uuid4

from app.accounting.selection import resolve_account
from app.correction_email.base import CorrectionEmailDrafter
from app.correction_email.eligibility import supplier_fixable_issues
from app.correction_email.schemas import CorrectionEmailDraft
from app.documents.models import DocumentRecord
from app.documents.repository import DocumentRepository
from app.documents.schemas import (
    DECIDED_STATUSES,
    REVIEWABLE_STATUSES,
    DocumentCorrectionRequest,
    DocumentStatus,
)
from app.invoices.validation import (
    IssueSeverity,
    ValidationIssue,
    validate_invoice,
    validate_receipt,
)
from app.pipeline import (
    ExtractionState,
    PipelineContext,
    ValidationState,
    build_document_pipeline,
)
from app.providers.azure_openai_correction_email import AzureOpenAICorrectionEmailDrafter


class DocumentNotFoundError(RuntimeError):
    pass


class DocumentProcessingError(RuntimeError):
    pass


class DocumentReviewConflictError(RuntimeError):
    """The review is in a state that does not allow this action (HTTP 409)."""


class DocumentService:
    def __init__(
        self,
        *,
        repository: DocumentRepository,
        upload_dir: Path,
        correction_email_drafter: CorrectionEmailDrafter | None = None,
    ) -> None:
        self.repository = repository
        self.upload_dir = upload_dir
        self._correction_email_drafter = correction_email_drafter

    def process(
        self,
        *,
        original_filename: str,
        content_type: str,
        content: bytes,
        suffix: str,
    ) -> DocumentRecord:
        record_id = str(uuid4())
        stored_filename = f"{record_id}{suffix}"
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        stored_path = self.upload_dir / stored_filename
        stored_path.write_bytes(content)
        self.repository.create_processing(
            record_id=record_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
        )

        try:
            context = build_document_pipeline(duplicate_registry=self.repository).run(
                PipelineContext(document_path=stored_path)
            )
        except Exception as error:
            message = str(error) or error.__class__.__name__
            self.repository.save_failure(record_id, message)
            raise DocumentProcessingError(message) from error

        issues = context.validation.issues if context.validation is not None else []
        return self.repository.save_result(
            record_id,
            status=status_for_issues(issues),
            classification=context.classification,
            extraction=context.extraction,
            document_review=context.document_review,
            validation=context.validation,
            gl_suggestion=context.gl_suggestion,
        )

    def get(self, record_id: str) -> DocumentRecord:
        record = self.repository.get(record_id)
        if record is None:
            raise DocumentNotFoundError("Document not found")
        return record

    def stored_path(self, record: DocumentRecord) -> Path:
        return self.upload_dir / Path(record.stored_filename).name

    def correct(
        self, record_id: str, corrections: DocumentCorrectionRequest
    ) -> DocumentRecord:
        """Apply Maya's edits, mark them as human, and re-run Plurobi policy."""
        record = self._reviewable(record_id)
        extraction = ExtractionState.model_validate(record.extraction or {})
        sources = dict(extraction.field_sources)

        if extraction.invoice is not None:
            changes = (
                corrections.invoice.model_dump(exclude_unset=True)
                if corrections.invoice
                else {}
            )
            invoice = extraction.invoice.model_copy(update=changes)
            _mark_human(sources, extraction.invoice, invoice, changes)
            extraction = ExtractionState(invoice=invoice, field_sources=sources)
            issues = validate_invoice(
                invoice, duplicate_registry=self.repository.excluding(record_id)
            )
        elif extraction.receipt is not None:
            changes = (
                corrections.receipt.model_dump(exclude_unset=True)
                if corrections.receipt
                else {}
            )
            receipt = extraction.receipt.model_copy(update=changes)
            _mark_human(sources, extraction.receipt, receipt, changes)
            extraction = ExtractionState(receipt=receipt, field_sources=sources)
            issues = validate_receipt(receipt)
        else:
            raise DocumentReviewConflictError("This review has no extracted document to edit.")

        return self.repository.save_review(
            record_id,
            status=status_for_issues(issues),
            extraction=extraction,
            validation=ValidationState(issues=issues),
        )

    def select_gl_account(self, record_id: str, gl_account_code: str) -> DocumentRecord:
        self._reviewable(record_id)
        account = resolve_account(gl_account_code)
        return self.repository.update(record_id, selected_gl_account_code=account.code.value)

    def decide(self, record_id: str, decision: DocumentStatus) -> DocumentRecord:
        record = self._reviewable(record_id)
        if decision == "approved":
            issues = ValidationState.model_validate(record.validation or {}).issues
            if any(issue.severity == IssueSeverity.error for issue in issues):
                raise DocumentReviewConflictError(
                    "Resolve all validation errors before approving."
                )
            try:
                resolve_account(record.selected_gl_account_code or "")
            except ValueError as error:
                raise DocumentReviewConflictError(
                    "Select a Plurobi GL account before approving."
                ) from error
        return self.repository.update(record_id, status=decision)

    def draft_correction_email(self, record_id: str) -> CorrectionEmailDraft:
        """Generate on demand; nothing is stored and nothing is sent."""
        record = self._reviewable(record_id)
        extraction = ExtractionState.model_validate(record.extraction or {})
        document = extraction.invoice or extraction.receipt
        if document is None:
            raise DocumentReviewConflictError("This review has no extracted document.")
        issues = supplier_fixable_issues(
            ValidationState.model_validate(record.validation or {}).issues
        )
        if not issues:
            raise DocumentReviewConflictError(
                "There are no supplier-fixable errors to write to the supplier about."
            )
        recipient = (
            document.vendor_name if extraction.invoice is not None else document.merchant_name
        )
        if self._correction_email_drafter is None:
            self._correction_email_drafter = AzureOpenAICorrectionEmailDrafter()
        content = self._correction_email_drafter.draft(document, issues)
        return CorrectionEmailDraft(
            recipient_name=recipient or "Supplier",
            subject=content.subject,
            body=content.body,
            issue_codes=[issue.code for issue in issues],
        )

    def delete(self, record_id: str) -> None:
        record = self.get(record_id)
        stored_path = self.stored_path(record)
        self.repository.delete(record_id)
        stored_path.unlink(missing_ok=True)

    def _reviewable(self, record_id: str) -> DocumentRecord:
        record = self.get(record_id)
        if record.status in DECIDED_STATUSES:
            raise DocumentReviewConflictError(
                f"This document is already {record.status} and can no longer change."
            )
        if record.status not in REVIEWABLE_STATUSES:
            raise DocumentReviewConflictError("Only a completed review can be changed.")
        return record


def _mark_human(
    sources: dict[str, str],
    before: object,
    after: object,
    changes: dict[str, object],
) -> None:
    for field in changes:
        if getattr(before, field) != getattr(after, field):
            sources[field] = "human"


def status_for_issues(issues: list[ValidationIssue]) -> DocumentStatus:
    if any(issue.severity == IssueSeverity.error for issue in issues):
        return "needs_review"
    return "ready"
