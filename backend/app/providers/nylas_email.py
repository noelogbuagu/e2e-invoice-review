from dataclasses import dataclass

from nylas import Client
from nylas.models.webhooks import CreateWebhookRequest, WebhookTriggers

from app.correction_email.base import CorrectionEmailDeliveryError, SentEmail


@dataclass(frozen=True)
class CreatedWebhook:
    id: str
    secret: str


class NylasEmailProvider:
    """Keep Nylas SDK objects behind a provider-independent boundary."""

    def __init__(
        self,
        *,
        api_key: str,
        api_uri: str,
        grant_id: str,
    ) -> None:
        if not api_key or not grant_id:
            raise CorrectionEmailDeliveryError(
                "Configure NYLAS_API_KEY and NYLAS_GRANT_ID before sending email."
            )
        self._client = Client(api_key=api_key, api_uri=api_uri)
        self._grant_id = grant_id

    def send(
        self,
        *,
        to_email: str,
        subject: str,
        body: str,
        reply_to_message_id: str | None = None,
    ) -> SentEmail:
        request_body: dict[str, object] = {
            "to": [{"email": to_email}],
            "subject": subject,
            "body": body,
        }
        if reply_to_message_id:
            request_body["reply_to_message_id"] = reply_to_message_id
        try:
            response = self._client.messages.send(
                identifier=self._grant_id,
                request_body=request_body,
            )
            message = response.data
            message_id = message.id
            thread_id = message.thread_id
            if not message_id or not thread_id:
                raise CorrectionEmailDeliveryError(
                    "Nylas sent the message but did not return message or thread IDs."
                )
            return SentEmail(message_id=message_id, thread_id=thread_id)
        except CorrectionEmailDeliveryError:
            raise
        except Exception as error:
            raise CorrectionEmailDeliveryError(
                "Nylas could not send the correction email."
            ) from error

    def download_attachment(
        self, *, message_id: str, attachment_id: str
    ) -> bytes:
        try:
            return self._client.attachments.download_bytes(
                identifier=self._grant_id,
                attachment_id=attachment_id,
                query_params={"message_id": message_id},
            )
        except Exception as error:
            raise CorrectionEmailDeliveryError(
                "Nylas could not download the supplier attachment."
            ) from error


def create_message_webhook(
    *,
    api_key: str,
    api_uri: str,
    webhook_url: str,
    notification_email: str,
) -> CreatedWebhook:
    client = Client(api_key=api_key, api_uri=api_uri)
    request = CreateWebhookRequest(
        trigger_types=[WebhookTriggers.MESSAGE_CREATED],
        webhook_url=webhook_url,
        description="Supplier correction replies",
        notification_email_addresses=[notification_email],
    )
    webhook, _, _ = client.webhooks.create(request_body=request)
    return CreatedWebhook(id=webhook.id, secret=webhook.webhook_secret)
