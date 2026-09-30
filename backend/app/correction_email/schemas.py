from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _email(value: str) -> str:
    value = value.strip()
    local, separator, domain = value.rpartition("@")
    if not separator or not local or "." not in domain or len(value) > 320:
        raise ValueError("Enter a valid email address.")
    return value


class CorrectionEmailContent(BaseModel):
    """What the model writes. The recipient is set deterministically from the document."""

    subject: str = Field(min_length=1, max_length=998)
    body: str = Field(min_length=1, max_length=50_000)


class CorrectionEmailDraft(CorrectionEmailContent):
    recipient_name: str
    issue_codes: list[str]


class CorrectionEmailSendRequest(CorrectionEmailContent):
    to_email: str

    _valid_email = field_validator("to_email")(_email)


class CorrectionThreadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    attempt_number: int
    status: str
    to_email: str
    subject: str
    body: str
    issue_codes: list[str]
    sent_at: datetime | None
    received_at: datetime | None
    inbound_from_email: str | None


class NylasAttachment(BaseModel):
    id: str
    content_type: str
    filename: str
    size: int = Field(ge=0)
    is_inline: bool = False


class NylasSender(BaseModel):
    name: str = ""
    email: str

    _valid_email = field_validator("email")(_email)


class NylasMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    grant_id: str
    thread_id: str
    subject: str = ""
    body: str = ""
    snippet: str = ""
    folders: list[str] = Field(default_factory=list)
    from_: list[NylasSender] = Field(default_factory=list, alias="from")
    attachments: list[NylasAttachment] = Field(default_factory=list)


class NylasWebhookEvent(BaseModel):
    id: str
    type: str
    data: dict[str, object]
