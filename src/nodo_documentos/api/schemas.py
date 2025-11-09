from datetime import datetime
from typing import Annotated, Literal
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
    clinic_name: str = Field(min_length=1, description="The unique name of the clinic")
    s3_url: LongString


class DocumentResponse(BaseModel):
    doc_id: UUID
    created_by: CI
    health_user_ci: CI
    clinic_name: str
    created_at: datetime
    s3_url: LongString

    model_config = ConfigDict(from_attributes=True)


class AuthorizationDecision(BaseModel):
    allowed: bool
    reason: str | None = None


class PresignedUploadRequest(BaseModel):
    file_name: Annotated[str, Field(min_length=1, max_length=255)]
    content_type: Annotated[str | None, Field(default=None, max_length=128)]
    clinic_name: str = Field(min_length=1, description="The unique name of the clinic")


class PresignedUploadResponse(BaseModel):
    upload_url: AnyUrl
    s3_url: AnyUrl
    object_key: LongString
    expires_in_seconds: Annotated[int, Field(gt=0)]


class Message(BaseModel):
    """A message in a conversation."""

    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    """Request for chat query."""

    query: str = Field(min_length=1, max_length=2000, description="User question")
    conversation_history: list[Message] = Field(
        default_factory=list,
        max_length=20,
        description="Previous conversation messages",
    )
    health_user_ci: CI = Field(description="Patient whose documents to search")
    document_id: UUIDStr | None = Field(
        default=None, description="Optional specific document ID"
    )


class ChunkSource(BaseModel):
    """Source chunk used in the response."""

    document_id: str = Field(description="Document ID")
    chunk_id: str = Field(description="Chunk ID")
    text: str = Field(description="Full chunk text")
    similarity_score: float = Field(description="Similarity score from vector search")
    page_number: int | None = Field(default=None, description="Page number")
    section_title: str | None = Field(default=None, description="Section title")


class ChatResponse(BaseModel):
    """Response from chat query."""

    answer: str = Field(description="LLM-generated answer")
    sources: list[ChunkSource] = Field(description="Source chunks used")
