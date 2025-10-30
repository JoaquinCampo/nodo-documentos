from sqlalchemy.ext.asyncio import AsyncSession

from nodo_documentos.db.repos.clinical_history_access import (
    ClinicalHistoryAccessRepository,
)
from nodo_documentos.db.repos.document import DocumentRepository


def get_document_repository(session: AsyncSession) -> DocumentRepository:
    return DocumentRepository(session)


def get_clinical_history_access_repository(
    session: AsyncSession,
) -> ClinicalHistoryAccessRepository:
    return ClinicalHistoryAccessRepository(session)
