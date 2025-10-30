from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, Field

CI = Annotated[str, Field(pattern=r"^\d{8}$")]
LongString = Annotated[str, Field(min_length=1, max_length=512)]
UUIDStr = Annotated[
    str,
    Field(
        pattern=(
            r"^[0-9a-fA-F]{8}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{4}-"
            r"[0-9a-fA-F]{12}$"
        )
    ),
]


class DocumentCreateRequest(BaseModel):
    created_by: CI
    health_user_ci: CI
    clinic_id: UUIDStr
    s3_url: LongString


class DocumentResponse(BaseModel):
    doc_id: UUID
    created_by: CI
    health_user_ci: CI
    clinic_id: UUIDStr
    created_at: datetime
    s3_url: LongString

    model_config = ConfigDict(from_attributes=True)


class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str | None = None


class PresignedUploadRequest(BaseModel):
    file_name: Annotated[str, Field(min_length=1, max_length=255)]
    content_type: Annotated[str | None, Field(default=None, max_length=128)]
    clinic_id: UUIDStr


class PresignedUploadResponse(BaseModel):
    upload_url: AnyUrl
    s3_url: AnyUrl
    object_key: LongString
    expires_in_seconds: Annotated[int, Field(gt=0)]
