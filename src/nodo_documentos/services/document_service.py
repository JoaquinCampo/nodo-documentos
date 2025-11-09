from nodo_documentos.api.schemas import CI, LongString
from nodo_documentos.db.models import Document
from nodo_documentos.db.repos.document import DocumentRepository


class DocumentService:
    """Business operations tied to clinical documents."""

    def __init__(self, document_repo: DocumentRepository) -> None:
        self._document_repo = document_repo

    async def create_document(
        self,
        *,
        created_by: CI,
        health_user_ci: CI,
        clinic_name: str,
        s3_url: LongString,
    ) -> Document:
        """Register a newly uploaded document."""

        return await self._document_repo.create(
            created_by=created_by,
            health_user_ci=health_user_ci,
            clinic_name=clinic_name,
            s3_url=s3_url,
        )

    async def list_documents_for_health_user(
        self, health_user_ci: CI
    ) -> list[Document]:
        """Return all documents available for a particular patient."""

        return await self._document_repo.list_by_health_user(health_user_ci)
