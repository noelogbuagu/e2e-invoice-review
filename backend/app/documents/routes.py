from collections.abc import Iterator
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from app.config import AppConfig
from app.correction_email.base import (
    CorrectionEmailDeliveryError,
    CorrectionEmailDraftingError,
)
from app.correction_email.schemas import (
    CorrectionEmailDraft,
    CorrectionEmailSendRequest,
    CorrectionThreadResponse,
)
from app.documents.repository import DocumentRepository
from app.documents.schemas import (
    CorrectionEmailSendResponse,
    DecisionRequest,
    DocumentCorrectionRequest,
    DocumentResponse,
    GlSelectionRequest,
)
from app.documents.service import (
    DocumentNotFoundError,
    DocumentProcessingError,
    DocumentReviewConflictError,
    DocumentService,
)
from app.providers.nylas_email import NylasEmailProvider

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        yield session


def get_repository(session: Annotated[Session, Depends(get_session)]) -> DocumentRepository:
    return DocumentRepository(session)


def build_service(request: Request, repository: DocumentRepository) -> DocumentService:
    config: AppConfig = request.app.state.config
    settings = request.app.state.settings
    sender = None
    if settings.nylas_api_key and settings.nylas_grant_id:
        sender = NylasEmailProvider(
            api_key=settings.nylas_api_key,
            api_uri=settings.nylas_api_uri,
            grant_id=settings.nylas_grant_id,
        )
    return DocumentService(
        repository=repository,
        upload_dir=config.upload_dir,
        correction_email_sender=sender,
    )


@router.get("", response_model=list[DocumentResponse])
def list_documents(
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> list[DocumentResponse]:
    return [DocumentResponse.model_validate(record) for record in repository.list()]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    service = build_service(request, repository)
    try:
        return DocumentResponse.model_validate(service.get(document_id))
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get("/{document_id}/file")
def get_document_file(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> FileResponse:
    service = build_service(request, repository)
    try:
        record = service.get(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    path = service.stored_path(record)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored document file was not found.")
    return FileResponse(
        path,
        media_type=record.content_type,
        filename=record.original_filename,
        content_disposition_type="inline",
    )


@router.put("/{document_id}", response_model=DocumentResponse)
def correct_document(
    document_id: str,
    corrections: DocumentCorrectionRequest,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    service = build_service(request, repository)
    try:
        return DocumentResponse.model_validate(service.correct(document_id, corrections))
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.put("/{document_id}/accounting", response_model=DocumentResponse)
def select_gl_account(
    document_id: str,
    body: GlSelectionRequest,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    service = build_service(request, repository)
    try:
        record = service.select_gl_account(document_id, body.gl_account_code)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return DocumentResponse.model_validate(record)


@router.post("/{document_id}/decision", response_model=DocumentResponse)
def decide_document(
    document_id: str,
    body: DecisionRequest,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    service = build_service(request, repository)
    try:
        return DocumentResponse.model_validate(service.decide(document_id, body.decision))
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@router.post("/{document_id}/correction-email", response_model=CorrectionEmailDraft)
def draft_correction_email(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> CorrectionEmailDraft:
    service = build_service(request, repository)
    try:
        return service.draft_correction_email(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except CorrectionEmailDraftingError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.post(
    "/{document_id}/correction-email/send",
    response_model=CorrectionEmailSendResponse,
)
def send_correction_email(
    document_id: str,
    body: CorrectionEmailSendRequest,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> CorrectionEmailSendResponse:
    service = build_service(request, repository)
    try:
        document, thread = service.send_correction_email(document_id, body)
        return CorrectionEmailSendResponse(
            document=DocumentResponse.model_validate(document),
            thread=CorrectionThreadResponse.model_validate(thread),
        )
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except DocumentReviewConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except CorrectionEmailDeliveryError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error


@router.get(
    "/{document_id}/correction-threads",
    response_model=list[CorrectionThreadResponse],
)
def list_correction_threads(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> list[CorrectionThreadResponse]:
    service = build_service(request, repository)
    try:
        service.get(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return [
        CorrectionThreadResponse.model_validate(thread)
        for thread in repository.list_correction_threads(document_id)
    ]


@router.post("/{document_id}/supplier-reply", response_model=DocumentResponse)
def record_supplier_reply(
    document_id: str,
    request: Request,
    file: Annotated[UploadFile, File()],
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    config: AppConfig = request.app.state.config
    original_filename, content_type, payload, suffix = _read_upload(file, config)
    service = build_service(request, repository)
    thread = repository.latest_correction_thread(document_id)
    if thread is None or thread.status != "awaiting_supplier":
        raise HTTPException(
            status_code=409,
            detail="This review is not awaiting a supplier reply.",
        )
    repository.record_supplier_reply(
        thread,
        from_email=thread.to_email,
        nylas_message_id=None,
    )
    try:
        document = service.reprocess_supplier_reply(
            document_id,
            original_filename=original_filename,
            content_type=content_type,
            content=payload,
            suffix=suffix,
        )
    except (DocumentNotFoundError, DocumentReviewConflictError) as error:
        repository.complete_supplier_reply(thread.id, failed=True)
        raise HTTPException(status_code=409, detail=str(error)) from error
    except DocumentProcessingError as error:
        repository.complete_supplier_reply(thread.id, failed=True)
        raise HTTPException(status_code=502, detail=str(error)) from error
    repository.complete_supplier_reply(thread.id)
    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: str,
    request: Request,
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> Response:
    service = build_service(request, repository)
    try:
        service.delete(document_id)
    except DocumentNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    file: Annotated[UploadFile, File()],
    repository: Annotated[DocumentRepository, Depends(get_repository)],
) -> DocumentResponse:
    config: AppConfig = request.app.state.config
    original_filename, content_type, payload, suffix = _read_upload(file, config)
    service = build_service(request, repository)
    try:
        record = service.process(
            original_filename=original_filename,
            content_type=content_type,
            content=payload,
            suffix=suffix,
        )
    except DocumentProcessingError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return DocumentResponse.model_validate(record)


def _read_upload(
    file: UploadFile, config: AppConfig
) -> tuple[str, str, bytes, str]:
    content_type = file.content_type or "application/octet-stream"
    suffix = ALLOWED_CONTENT_TYPES.get(content_type)
    if suffix is None:
        raise HTTPException(
            status_code=415,
            detail="Use a PDF, JPEG, or PNG document.",
        )

    payload = file.file.read(config.max_upload_bytes + 1)
    if not payload:
        raise HTTPException(status_code=422, detail="Uploaded document is empty.")
    if len(payload) > config.max_upload_bytes:
        raise HTTPException(
            status_code=413,
            detail="The Azure F0 tutorial limit is 4 MB per document.",
        )

    original_filename = Path(file.filename or "document").name[:255]
    return original_filename, content_type, payload, suffix
