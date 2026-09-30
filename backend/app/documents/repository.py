from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.accounting.catalog import GlAccountSuggestion
from app.document_review.schemas import DocumentReview
from app.documents.models import CorrectionThreadRecord, DocumentRecord
from app.documents.schemas import DocumentStatus
from app.invoices.duplicate import DuplicateRegistry, InvoiceKey
from app.pipeline.base import DocumentClassification, ExtractionState, ValidationState


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create_processing(
        self,
        *,
        record_id: str,
        original_filename: str,
        stored_filename: str,
        content_type: str,
    ) -> DocumentRecord:
        record = DocumentRecord(
            id=record_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            content_type=content_type,
            status="processing",
        )
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get(self, record_id: str) -> DocumentRecord | None:
        return self.session.get(DocumentRecord, record_id)

    def list(self) -> list[DocumentRecord]:
        statement = select(DocumentRecord).order_by(
            DocumentRecord.created_at.desc(), DocumentRecord.id.desc()
        )
        return list(self.session.scalars(statement))

    def list_correction_threads(
        self, record_id: str
    ) -> list[CorrectionThreadRecord]:
        statement = (
            select(CorrectionThreadRecord)
            .where(CorrectionThreadRecord.document_id == record_id)
            .order_by(CorrectionThreadRecord.attempt_number.desc())
        )
        return list(self.session.scalars(statement))

    def latest_correction_thread(
        self, record_id: str
    ) -> CorrectionThreadRecord | None:
        threads = self.list_correction_threads(record_id)
        return threads[0] if threads else None

    def correction_thread_for_nylas_thread(
        self, nylas_thread_id: str
    ) -> CorrectionThreadRecord | None:
        statement = (
            select(CorrectionThreadRecord)
            .where(
                CorrectionThreadRecord.nylas_thread_id == nylas_thread_id,
                CorrectionThreadRecord.status == "awaiting_supplier",
            )
            .order_by(CorrectionThreadRecord.attempt_number.desc())
        )
        return self.session.scalar(statement.limit(1))

    def inbound_message_exists(self, message_id: str) -> bool:
        statement = select(CorrectionThreadRecord.id).where(
            CorrectionThreadRecord.inbound_nylas_message_id == message_id
        )
        return self.session.scalar(statement.limit(1)) is not None

    def outbound_message_exists(self, message_id: str) -> bool:
        statement = select(CorrectionThreadRecord.id).where(
            CorrectionThreadRecord.outbound_nylas_message_id == message_id
        )
        return self.session.scalar(statement.limit(1)) is not None

    def create_correction_thread(
        self,
        *,
        document_id: str,
        to_email: str,
        subject: str,
        body: str,
        issue_codes: list[str],
        nylas_thread_id: str,
        outbound_nylas_message_id: str,
    ) -> CorrectionThreadRecord:
        attempt = (
            self.session.scalar(
                select(func.count(CorrectionThreadRecord.id)).where(
                    CorrectionThreadRecord.document_id == document_id
                )
            )
            or 0
        ) + 1
        thread = CorrectionThreadRecord(
            id=str(uuid4()),
            document_id=document_id,
            attempt_number=attempt,
            status="awaiting_supplier",
            to_email=to_email,
            subject=subject,
            body=body,
            issue_codes=issue_codes,
            nylas_thread_id=nylas_thread_id,
            outbound_nylas_message_id=outbound_nylas_message_id,
            sent_at=datetime.now(UTC),
        )
        self.session.add(thread)
        self.session.commit()
        self.session.refresh(thread)
        return thread

    def record_supplier_reply(
        self,
        thread: CorrectionThreadRecord,
        *,
        from_email: str,
        nylas_message_id: str | None,
    ) -> CorrectionThreadRecord:
        thread.status = "processing_reply"
        thread.inbound_from_email = from_email
        thread.inbound_nylas_message_id = nylas_message_id
        thread.received_at = datetime.now(UTC)
        self._commit_thread(thread)
        return thread

    def complete_supplier_reply(
        self, thread_id: str, *, failed: bool = False
    ) -> CorrectionThreadRecord:
        thread = self.session.get(CorrectionThreadRecord, thread_id)
        if thread is None:
            raise KeyError(thread_id)
        thread.status = "reply_failed" if failed else "reviewed"
        self._commit_thread(thread)
        return thread

    def save_result(
        self,
        record_id: str,
        *,
        status: DocumentStatus,
        classification: DocumentClassification | None,
        extraction: ExtractionState | None,
        document_review: DocumentReview | None,
        validation: ValidationState | None,
        gl_suggestion: GlAccountSuggestion | None,
    ) -> DocumentRecord:
        record = self._require(record_id)
        record.status = status
        record.classification = (
            classification.model_dump(mode="json") if classification is not None else None
        )
        record.extraction = (
            extraction.model_dump(mode="json") if extraction is not None else None
        )
        record.document_review = (
            document_review.model_dump(mode="json") if document_review is not None else None
        )
        record.validation = (
            validation.model_dump(mode="json") if validation is not None else None
        )
        record.gl_suggestion = (
            gl_suggestion.model_dump(mode="json") if gl_suggestion is not None else None
        )
        record.selected_gl_account_code = (
            gl_suggestion.account_code.value if gl_suggestion is not None else None
        )
        record.error_message = None
        self._set_duplicate_key(record, extraction)
        self._commit(record)
        return record

    def prepare_reprocessing(
        self,
        record_id: str,
        *,
        original_filename: str,
        stored_filename: str,
        content_type: str,
    ) -> DocumentRecord:
        record = self._require(record_id)
        record.original_filename = original_filename
        record.stored_filename = stored_filename
        record.content_type = content_type
        record.status = "processing"
        record.error_message = None
        self._commit(record)
        return record

    def save_review(
        self,
        record_id: str,
        *,
        status: DocumentStatus,
        extraction: ExtractionState,
        validation: ValidationState,
    ) -> DocumentRecord:
        """Persist Maya's corrected fields and the re-run policy result."""
        record = self._require(record_id)
        record.status = status
        record.extraction = extraction.model_dump(mode="json")
        record.validation = validation.model_dump(mode="json")
        self._set_duplicate_key(record, extraction)
        self._commit(record)
        return record

    def update(self, record_id: str, **changes: str | None) -> DocumentRecord:
        """Set scalar columns such as status or selected_gl_account_code."""
        record = self._require(record_id)
        for name, value in changes.items():
            setattr(record, name, value)
        self._commit(record)
        return record

    def save_failure(self, record_id: str, message: str) -> DocumentRecord:
        record = self._require(record_id)
        record.status = "failed"
        record.error_message = message
        self._commit(record)
        return record

    def delete(self, record_id: str) -> None:
        record = self._require(record_id)
        for thread in self.list_correction_threads(record_id):
            self.session.delete(thread)
        self.session.delete(record)
        self.session.commit()

    def is_registered(self, key: InvoiceKey) -> bool:
        return self.duplicate_exists(key.vendor_name, key.invoice_number)

    def duplicate_exists(
        self, vendor_name: str, invoice_number: str, *, exclude_id: str | None = None
    ) -> bool:
        statement = select(DocumentRecord).where(
            DocumentRecord.vendor_name == vendor_name,
            DocumentRecord.invoice_number == invoice_number,
        )
        if exclude_id is not None:
            statement = statement.where(DocumentRecord.id != exclude_id)
        return self.session.scalar(statement.limit(1)) is not None

    def excluding(self, record_id: str) -> DuplicateRegistry:
        """Duplicate registry that ignores the record being re-validated."""
        return _ExcludingRegistry(self, record_id)

    @staticmethod
    def _set_duplicate_key(record: DocumentRecord, extraction: ExtractionState | None) -> None:
        invoice = extraction.invoice if extraction is not None else None
        record.vendor_name = invoice.vendor_name if invoice is not None else None
        record.invoice_number = invoice.invoice_number if invoice is not None else None

    def _require(self, record_id: str) -> DocumentRecord:
        record = self.get(record_id)
        if record is None:
            raise KeyError(record_id)
        return record

    def _commit(self, record: DocumentRecord) -> None:
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)

    def _commit_thread(self, thread: CorrectionThreadRecord) -> None:
        self.session.add(thread)
        self.session.commit()
        self.session.refresh(thread)


class _ExcludingRegistry:
    def __init__(self, repository: DocumentRepository, record_id: str) -> None:
        self._repository = repository
        self._record_id = record_id

    def is_registered(self, key: InvoiceKey) -> bool:
        return self._repository.duplicate_exists(
            key.vendor_name, key.invoice_number, exclude_id=self._record_id
        )
