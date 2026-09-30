from dataclasses import dataclass
from typing import Protocol

from app.correction_email.schemas import CorrectionEmailContent
from app.invoices.validation import ValidationIssue
from app.schemas.invoice.model import Invoice
from app.schemas.receipt.model import Receipt


class CorrectionEmailDraftingError(RuntimeError):
    pass


class CorrectionEmailDrafter(Protocol):
    def draft(
        self, document: Invoice | Receipt, issues: list[ValidationIssue]
    ) -> CorrectionEmailContent: ...


class CorrectionEmailDeliveryError(RuntimeError):
    pass


@dataclass(frozen=True)
class SentEmail:
    message_id: str
    thread_id: str


class CorrectionEmailSender(Protocol):
    def send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        reply_to_message_id: str | None = None,
    ) -> SentEmail: ...

    def download_attachment(
        self, *, message_id: str, attachment_id: str
    ) -> bytes: ...
