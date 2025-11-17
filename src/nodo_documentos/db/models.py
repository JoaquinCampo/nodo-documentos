import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

LOCAL_TIMEZONE = timezone(timedelta(hours=-3))


class Base(DeclarativeBase):
    """Base declarative class for all ORM models."""


class Document(Base):
    """Stores metadata for every clinical document uploaded to the system."""

    __tablename__ = "documents"

    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="The unique identifier for the document.",
    )
    created_by: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
        doc="The CI of the user who uploaded the document.",
    )
    health_user_ci: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
        doc="The CI of the health user who the document is for.",
    )
    clinic_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
        index=True,
        doc="The name of the clinic.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(LOCAL_TIMEZONE),
        server_default=func.now(),
        doc="The timestamp of when the document was uploaded.",
    )
    s3_url: Mapped[str | None] = mapped_column(
        String(512),
        nullable=True,
        doc="The URL of the document in S3.",
    )
    title: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        doc="Title of the document.",
    )
    description: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
        doc="Description of the document.",
    )
    content_type: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        doc="MIME type of the document.",
    )
    provider_name: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        doc="Name of the provider.",
    )
