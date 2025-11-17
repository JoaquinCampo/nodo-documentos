from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from nodo_documentos.api.schemas import CI, LongString
from nodo_documentos.db.models import Document


class DocumentRepository:
    """Data access layer for clinical documents."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        created_by: CI,
        health_user_ci: CI,
        clinic_name: str,
        s3_url: LongString | None = None,
        title: str | None = None,
        description: str | None = None,
        content_type: str | None = None,
        provider_name: str | None = None,
    ) -> Document:
        """Persist a new document metadata row linked to the uploaded file."""
        document = Document(
            created_by=created_by,
            health_user_ci=health_user_ci,
            clinic_name=clinic_name,
            s3_url=s3_url,
            title=title,
            description=description,
            content_type=content_type,
            provider_name=provider_name,
        )
        self._session.add(document)
        await self._session.flush()
        await self._session.refresh(document)
        return document

    async def list_by_health_user(self, health_user_ci: CI) -> list[Document]:
        """Return every document for a specific patient ordered by creation time."""

        stmt = (
            select(Document)
            .where(Document.health_user_ci == health_user_ci)
            .order_by(Document.created_at.desc(), Document.doc_id.desc())
        )
        result = await self._session.scalars(stmt)
        return list[Document](result.all())
