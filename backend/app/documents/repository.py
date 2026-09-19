from sqlalchemy import select
from sqlalchemy.orm import Session

from app.accounting.catalog import GlAccountSuggestion
from app.documents.models import DocumentRecord
from app.documents.schemas import DocumentStatus
from app.invoices.duplicate import InvoiceKey
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

    def save_result(
        self,
        record_id: str,
        *,
        status: DocumentStatus,
        classification: DocumentClassification | None,
        extraction: ExtractionState | None,
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
        record.validation = (
            validation.model_dump(mode="json") if validation is not None else None
        )
        record.gl_suggestion = (
            gl_suggestion.model_dump(mode="json") if gl_suggestion is not None else None
        )
        record.error_message = None
        invoice = extraction.invoice if extraction is not None else None
        record.vendor_name = invoice.vendor_name if invoice is not None else None
        record.invoice_number = invoice.invoice_number if invoice is not None else None
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
        self.session.delete(record)
        self.session.commit()

    def is_registered(self, key: InvoiceKey) -> bool:
        return self.duplicate_exists(key.vendor_name, key.invoice_number)

    def duplicate_exists(self, vendor_name: str, invoice_number: str) -> bool:
        statement = select(DocumentRecord).where(
            DocumentRecord.vendor_name == vendor_name,
            DocumentRecord.invoice_number == invoice_number,
        )
        return self.session.scalar(statement.limit(1)) is not None

    def _require(self, record_id: str) -> DocumentRecord:
        record = self.get(record_id)
        if record is None:
            raise KeyError(record_id)
        return record

    def _commit(self, record: DocumentRecord) -> None:
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
