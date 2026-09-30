import hashlib
import hmac
import logging
from collections.abc import Callable
from http import HTTPStatus

from fastapi import APIRouter, BackgroundTasks, Header, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.config import AppConfig, Settings
from app.correction_email.schemas import NylasMessage, NylasWebhookEvent
from app.documents.repository import DocumentRepository
from app.documents.routes import ALLOWED_CONTENT_TYPES
from app.documents.service import DocumentService
from app.providers.nylas_email import NylasEmailProvider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["email webhooks"])


def verify_nylas_signature(
    body: bytes, signature: str | None, secret: str
) -> bool:
    if not signature or not secret:
        return False
    expected = hmac.new(
        secret.encode(),
        body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(
        expected,
        signature.removeprefix("sha256="),
    )


@router.get("")
def verify_webhook(request: Request) -> PlainTextResponse:
    challenge = request.query_params.get("challenge")
    if not challenge:
        return PlainTextResponse(
            "Missing challenge",
            status_code=HTTPStatus.BAD_REQUEST,
        )
    return PlainTextResponse(challenge)


@router.post("")
async def receive_message(
    request: Request,
    background_tasks: BackgroundTasks,
    x_nylas_signature: str | None = Header(default=None),
) -> Response:
    settings: Settings = request.app.state.settings
    body = await request.body()
    if len(body) > 1024 * 1024:
        return PlainTextResponse(
            "Webhook payload is too large",
            status_code=HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
        )
    if not verify_nylas_signature(body, x_nylas_signature, settings.webhook_secret):
        return PlainTextResponse(
            "Signature verification failed",
            status_code=HTTPStatus.UNAUTHORIZED,
        )

    try:
        event = NylasWebhookEvent.model_validate_json(body)
        message = NylasMessage.model_validate(event.data["object"])
    except (KeyError, ValidationError):
        return PlainTextResponse(
            "Invalid webhook payload",
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    if event.type != "message.created":
        return Response(status_code=HTTPStatus.NO_CONTENT)

    folders = {folder.upper() for folder in message.folders}
    if "INBOX" not in folders:
        return Response(status_code=HTTPStatus.NO_CONTENT)

    session_factory: Callable[[], Session] = request.app.state.session_factory
    with session_factory() as session:
        repository = DocumentRepository(session)
        if repository.inbound_message_exists(
            message.id
        ) or repository.outbound_message_exists(message.id):
            return Response(status_code=HTTPStatus.NO_CONTENT)
        thread = repository.correction_thread_for_nylas_thread(message.thread_id)
        if thread is None:
            return Response(status_code=HTTPStatus.NO_CONTENT)

        sender = message.from_[0].email if message.from_ else ""
        if sender.casefold() != thread.to_email.casefold():
            logger.warning(
                "supplier_reply_sender_mismatch",
                extra={
                    "expected": thread.to_email,
                    "received": sender,
                    "message_id": message.id,
                },
            )
        attachment = next(
            (
                item
                for item in message.attachments
                if not item.is_inline
                and item.content_type in ALLOWED_CONTENT_TYPES
                and item.size <= request.app.state.config.max_upload_bytes
            ),
            None,
        )
        repository.record_supplier_reply(
            thread,
            from_email=sender,
            nylas_message_id=message.id,
        )
        if attachment is None:
            repository.complete_supplier_reply(thread.id, failed=True)
            repository.update(thread.document_id, status="needs_review")
            return Response(status_code=HTTPStatus.NO_CONTENT)

        # ponytail: in-process tasks can be lost on restart; replace with a durable outbox/queue
        # before using this outside the single-instance teaching demo.
        background_tasks.add_task(
            _process_supplier_attachment,
            session_factory=session_factory,
            config=request.app.state.config,
            settings=settings,
            document_id=thread.document_id,
            correction_thread_id=thread.id,
            message_id=message.id,
            attachment_id=attachment.id,
            filename=attachment.filename,
            content_type=attachment.content_type,
        )
    return Response(status_code=HTTPStatus.OK)


def _process_supplier_attachment(
    *,
    session_factory: Callable[[], Session],
    config: AppConfig,
    settings: Settings,
    document_id: str,
    correction_thread_id: str,
    message_id: str,
    attachment_id: str,
    filename: str,
    content_type: str,
) -> None:
    with session_factory() as session:
        repository = DocumentRepository(session)
        provider = NylasEmailProvider(
            api_key=settings.nylas_api_key,
            api_uri=settings.nylas_api_uri,
            grant_id=settings.nylas_grant_id,
        )
        try:
            content = provider.download_attachment(
                message_id=message_id,
                attachment_id=attachment_id,
            )
            if not content or len(content) > config.max_upload_bytes:
                raise ValueError("Supplier attachment is empty or exceeds 4 MB.")
            service = DocumentService(
                repository=repository,
                upload_dir=config.upload_dir,
            )
            service.reprocess_supplier_reply(
                document_id,
                original_filename=filename,
                content_type=content_type,
                content=content,
                suffix=ALLOWED_CONTENT_TYPES[content_type],
            )
        except Exception:
            logger.exception(
                "supplier_reply_processing_failed",
                extra={"document_id": document_id, "message_id": message_id},
            )
            repository.complete_supplier_reply(
                correction_thread_id,
                failed=True,
            )
            record = repository.get(document_id)
            if record is not None and record.status == "awaiting_supplier":
                repository.update(document_id, status="needs_review")
            return
        repository.complete_supplier_reply(correction_thread_id)
