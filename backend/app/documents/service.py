from pathlib import Path
from uuid import uuid4

from app.documents.models import DocumentRecord
from app.documents.repository import DocumentRepository
from app.documents.schemas import DocumentStatus
from app.invoices.validation import IssueSeverity, ValidationIssue
from app.pipeline import PipelineContext, build_document_pipeline


class DocumentNotFoundError(RuntimeError):
    pass


class DocumentProcessingError(RuntimeError):
    pass


class DocumentService:
    def __init__(self, *, repository: DocumentRepository, upload_dir: Path) -> None:
        self.repository = repository
        self.upload_dir = upload_dir

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
            validation=context.validation,
            gl_suggestion=context.gl_suggestion,
        )

    def get(self, record_id: str) -> DocumentRecord:
        record = self.repository.get(record_id)
        if record is None:
            raise DocumentNotFoundError("Document not found")
        return record

    def delete(self, record_id: str) -> None:
        record = self.repository.get(record_id)
        if record is None:
            raise DocumentNotFoundError(f"Document {record_id} was not found.")
        stored_path = self.upload_dir / Path(record.stored_filename).name
        self.repository.delete(record_id)
        stored_path.unlink(missing_ok=True)


def status_for_issues(issues: list[ValidationIssue]) -> DocumentStatus:
    if any(issue.severity == IssueSeverity.error for issue in issues):
        return "needs_review"
    return "ready"
