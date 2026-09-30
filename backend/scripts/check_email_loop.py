import hashlib
import hmac
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.correction_email.base import SentEmail
from app.correction_email.routes import verify_nylas_signature
from app.correction_email.schemas import CorrectionEmailSendRequest
from app.database import Base
from app.documents.models import DocumentRecord
from app.documents.repository import DocumentRepository
from app.documents.service import DocumentService
from app.invoices.validation import ValidationIssue
from app.pipeline.base import ExtractionState, ValidationState
from app.schemas.invoice.model import Invoice


class FakeSender:
    def __init__(self) -> None:
        self.reply_to: list[str | None] = []

    def send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        reply_to_message_id: str | None = None,
    ) -> SentEmail:
        self.reply_to.append(reply_to_message_id)
        attempt = len(self.reply_to)
        return SentEmail(message_id=f"message-{attempt}", thread_id="thread-1")

    def download_attachment(
        self, *, message_id: str, attachment_id: str
    ) -> bytes:
        raise NotImplementedError


def main() -> None:
    body = b'{"type":"message.created"}'
    signature = hmac.new(b"secret", body, hashlib.sha256).hexdigest()
    assert verify_nylas_signature(body, f"sha256={signature}", "secret")
    assert not verify_nylas_signature(body + b" ", signature, "secret")

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with TemporaryDirectory() as upload_dir, Session(engine) as session:
        repository = DocumentRepository(session)
        session.add(
            DocumentRecord(
                id="document-1",
                original_filename="invoice.pdf",
                stored_filename="document-1.pdf",
                content_type="application/pdf",
                status="needs_review",
                extraction=ExtractionState(
                    invoice=Invoice(vendor_name="Fictional Supplier")
                ).model_dump(mode="json"),
                validation=ValidationState(
                    issues=[
                        ValidationIssue(
                            code="vendor_vat_missing",
                            message="Supplier VAT ID is required.",
                        )
                    ]
                ).model_dump(mode="json"),
            )
        )
        session.commit()

        sender = FakeSender()
        service = DocumentService(
            repository=repository,
            upload_dir=Path(upload_dir),
            correction_email_sender=sender,
        )
        request = CorrectionEmailSendRequest(
            to_email="supplier@example.com",
            subject="Please correct invoice",
            body="Please attach a corrected invoice.",
        )
        document, first = service.send_correction_email("document-1", request)
        assert document.status == "awaiting_supplier"
        assert first.attempt_number == 1
        assert sender.reply_to == [None]

        repository.record_supplier_reply(
            first,
            from_email="supplier@example.com",
            nylas_message_id="reply-1",
        )
        repository.complete_supplier_reply(first.id)
        repository.update("document-1", status="needs_review")
        _, second = service.send_correction_email("document-1", request)
        assert second.attempt_number == 2
        assert sender.reply_to == [None, "reply-1"]

    print("PASS: correction attempts persist and replies stay in one Nylas thread")


if __name__ == "__main__":
    main()
