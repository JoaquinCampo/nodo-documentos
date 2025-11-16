from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from nodo_documentos.db.session import get_async_session
from nodo_documentos.services.chat_service import ChatService
from nodo_documentos.services.document_service import DocumentService
from nodo_documentos.services.factory import (
    get_chat_service,
    get_document_service,
    get_rag_service,
)
from nodo_documentos.services.rag_service import RAGService


async def document_service(
    session: AsyncSession = Depends(get_async_session),
) -> DocumentService:
    """Dependency that yields a document service."""

    return get_document_service(session)


def rag_service() -> RAGService:
    """Dependency that yields the RAG service (no session needed)."""
    return get_rag_service()


def chat_service() -> ChatService:
    """Dependency that yields the chat service (no session needed)."""
    return get_chat_service()
