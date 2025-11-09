from sqlalchemy.ext.asyncio import AsyncSession

from nodo_documentos.db.repos.factory import (
    get_clinical_history_access_repository,
    get_document_repository,
)
from nodo_documentos.services.clinical_history_access_service import (
    ClinicalHistoryAccessService,
)
from nodo_documentos.services.document_service import DocumentService
from nodo_documentos.services.rag_service import RAGService


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


def get_rag_service() -> RAGService:
    """Factory helper for the RAG service (no SQL session needed)."""
    from nodo_documentos.rag.chunking.chunker import get_chunker
    from nodo_documentos.rag.encoding.encoder import get_encoder
    from nodo_documentos.rag.parsing.parser import get_parser
    from nodo_documentos.rag.vector_db.db import get_vector_db

    vector_db = get_vector_db()
    pdf_parser = get_parser()
    pdf_chunker = get_chunker()
    encoder = get_encoder()

    return RAGService(vector_db, pdf_parser, pdf_chunker, encoder)
