from uuid import uuid4

from fastapi import APIRouter, Depends, status

from nodo_documentos.api.dependencies import document_service
from nodo_documentos.api.schemas import (
    DocumentCreateRequest,
    DocumentResponse,
    PresignedUploadRequest,
    PresignedUploadResponse,
)
from nodo_documentos.services.document_service import DocumentService
from nodo_documentos.utils.s3_utils import build_s3_uri, generate_presigned_put_url

router = APIRouter(prefix="/documents", tags=["documents"])


def _sanitize_file_name(file_name: str) -> str:
    trimmed = file_name.strip()
    normalized = trimmed.replace("\\", "/").split("/")[-1]
    return normalized or "upload"


@router.post(
    "",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    payload: DocumentCreateRequest,
    service: DocumentService = Depends(document_service),
) -> DocumentResponse:
    """Register a new clinical document and return its metadata."""

    document = await service.create_document(**payload.model_dump())
    return DocumentResponse.model_validate(document)


@router.post(
    "/upload-url",
    response_model=PresignedUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_upload_url(
    payload: PresignedUploadRequest,
) -> PresignedUploadResponse:
    """Return a presigned URL so the front-end can upload the binary to S3."""

    filename = _sanitize_file_name(payload.file_name)
    object_key = f"{payload.clinic_id}/{uuid4()}/{filename}"
    presigned = generate_presigned_put_url(
        key=object_key,
        content_type=payload.content_type,
    )

    return PresignedUploadResponse(
        upload_url=presigned.url,
        s3_url=build_s3_uri(object_key),
        object_key=object_key,
        expires_in_seconds=presigned.expires_in,
    )
