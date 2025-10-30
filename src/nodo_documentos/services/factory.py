from sqlalchemy.ext.asyncio import AsyncSession

from nodo_documentos.db.repos.factory import (
    get_clinical_history_access_repository,
    get_document_repository,
)
from nodo_documentos.services.clinical_history_access_service import (
    ClinicalHistoryAccessService,
)
from nodo_documentos.services.document_service import DocumentService


def get_document_service(session: AsyncSession) -> DocumentService:
    """Classic factory helper that wires the document service."""

    repo = get_document_repository(session)
    return DocumentService(repo)


def get_clinical_history_access_service(
    session: AsyncSession,
) -> ClinicalHistoryAccessService:
    """Classic factory helper for the clinical-history access service."""

    repo = get_clinical_history_access_repository(session)
    return ClinicalHistoryAccessService(repo)
