from pydantic import BaseModel


class CorrectionEmailContent(BaseModel):
    """What the model writes. The recipient is set deterministically from the document."""

    subject: str
    body: str


class CorrectionEmailDraft(CorrectionEmailContent):
    recipient_name: str
    issue_codes: list[str]
