from sqlalchemy.ext.asyncio import AsyncSession

from nodo_documentos.db.repos.document import DocumentRepository


def get_document_repository(session: AsyncSession) -> DocumentRepository:
    return DocumentRepository(session)
