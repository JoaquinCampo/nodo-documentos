from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AnyUrl, BaseModel, ConfigDict, Field, field_serializer

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
TextContent = Annotated[
    str, Field(max_length=100000, description="Text content of the document")
]


class DocumentCreateRequest(BaseModel):
    created_by: CI = Field(
        alias="health_worker_ci",
        description=(
            "CI of the user who created the document (also accepts 'health_worker_ci')"
        ),
    )
    health_user_ci: CI
    clinic_name: str = Field(min_length=1, description="The name of the clinic")
    s3_url: LongString | None = Field(
        default=None,
        alias="content_url",
        description="URL of the document in S3 (also accepts 'content_url')",
    )
    title: str | None = Field(
        default=None, max_length=255, description="Title of the document"
    )
    description: str | None = Field(
        default=None, max_length=1000, description="Description of the document"
    )
    content_type: str | None = Field(
        default=None, max_length=128, description="MIME type of the document"
    )
    provider_name: str | None = Field(default=None, description="Name of the provider")
    content: TextContent | None = Field(
        default=None,
        description="Text content of the document (for documents without file upload)",
    )

    model_config = ConfigDict(populate_by_name=True)


class DocumentResponse(BaseModel):
    doc_id: UUID
    created_by: CI = Field(
        alias="health_worker_ci",
        serialization_alias="health_worker_ci",
        description="CI of the user who created the document",
    )
    health_user_ci: CI
    clinic_name: str
    created_at: datetime
    s3_url: LongString | None = Field(
        default=None,
        alias="content_url",
        serialization_alias="content_url",
        description=(
            "Presigned HTTPS URL for downloading the document (expires after a period)"
        ),
    )
    title: str | None = None
    description: str | None = None
    content_type: str | None = None
    provider_name: str | None = None
    content: TextContent | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_serializer("s3_url", when_used="json")
    def serialize_content_url(self, value: str | None) -> str | None:
        """
        Transform internal S3 URI (s3://bucket/key) into presigned download URL.

        This serializer automatically converts the internal S3 URI into a presigned
        HTTPS URL that clients can use to download the document.
        """
        if not value:
            return None

        # If it's already an HTTPS URL, return as-is (shouldn't happen, but be safe)
        if value.startswith("https://"):
            return value

        # Generate presigned URL from S3 URI
        from nodo_documentos.utils.s3_utils import generate_presigned_get_url

        presigned = generate_presigned_get_url(s3_url=value)
        return presigned.url if presigned else None


class PresignedUploadRequest(BaseModel):
    file_name: Annotated[str, Field(min_length=1, max_length=255)]
    content_type: Annotated[str | None, Field(default=None, max_length=128)]
    clinic_name: str = Field(min_length=1, description="The name of the clinic")


class PresignedUploadResponse(BaseModel):
    upload_url: AnyUrl
    s3_url: AnyUrl
    object_key: LongString
    expires_in_seconds: Annotated[int, Field(gt=0)]


class Message(BaseModel):
    """A message in a conversation."""

    role: Literal["user", "assistant"] = Field(
        description=(
            "Message role: 'user' for user messages, 'assistant' for AI responses"
        )
    )
    content: str = Field(description="The message content")


class ChatRequest(BaseModel):
    """Request for chat query."""

    query: str = Field(min_length=1, max_length=2000, description="User question")
    conversation_history: list[Message] = Field(
        default_factory=list,
        max_length=20,
        description="Previous conversation messages",
    )
    health_user_ci: CI = Field(
        description="Patient's CI (8-digit identifier) whose documents to search"
    )
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
