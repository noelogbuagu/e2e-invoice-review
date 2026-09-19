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
