from typing import Sequence

from loguru import logger
from qdrant_client.models import ScoredPoint

from nodo_documentos.api.schemas import ChatRequest, ChatResponse, ChunkSource
from nodo_documentos.rag.encoding.encoder import EmbeddingEncoder
from nodo_documentos.rag.inference.service import CerebrasInferenceService
from nodo_documentos.rag.vector_db.db import VectorDB


class ChatService:
    """Service for chat-based document querying using RAG."""

    def __init__(
        self,
        vector_db: VectorDB,
        encoder: EmbeddingEncoder,
        inference_service: CerebrasInferenceService,
    ) -> None:
        self._vector_db = vector_db
        self._encoder = encoder
        self._inference_service = inference_service

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """
        Process a chat query using RAG.

        Args:
            request: Chat request with query, history, and ownership info

        Returns:
            Chat response with answer and sources

        Raises:
            ValueError: If no chunks found
        """
        logger.info(
            f"Processing chat query for health_user_ci={request.health_user_ci}, "
            f"document_id={request.document_id}"
        )

        logger.debug("Generating query embedding")
        query_embedding = self._encoder.embed(request.query)

        logger.debug("Searching vector database")
        chunks = self._vector_db.search(
            embedding=query_embedding,
            limit=10,
            health_user_ci=request.health_user_ci,
            document_id=request.document_id,
        )

        if not chunks:
            logger.warning("No chunks found for query")
            return ChatResponse(
                answer="I couldn't find relevant information in the documents.",
                sources=[],
            )

        logger.debug(f"Found {len(chunks)} relevant chunks")

        context = self._build_context(chunks)

        messages = self._build_messages(request, context)

        # 5. Generate response using Cerebras
        logger.debug("Generating LLM response")
        answer = self._inference_service.generate(
            messages=messages,
            temperature=0.7,
        )

        # 6. Format sources
        sources = self._format_sources(chunks)

        logger.success(f"Generated response: {len(answer)} characters")

        return ChatResponse(answer=answer, sources=sources)

    def _build_context(self, chunks: Sequence[ScoredPoint]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []

        for chunk in chunks:
            payload = chunk.payload or {}
            document_id = payload.get("document_id", "unknown")
            text = payload.get("text", "")
            page_number = payload.get("page_number")
            section_title = payload.get("section_title")

            context_part = f"[Document: {document_id}]\n{text}"
            if page_number:
                context_part += f"\n(Page {page_number}"
                if section_title:
                    context_part += f", Section: {section_title}"
                context_part += ")"
            context_part += "\n---\n"

            context_parts.append(context_part)

        return "\n".join(context_parts)

    def _build_messages(
        self, request: ChatRequest, context: str
    ) -> list[dict[str, str]]:
        """Build messages list for Cerebras API."""
        messages = []

        # System message
        system_message = (
            "You are a medical assistant helping healthcare workers understand "
            "patient documents. Use ONLY the provided context from the documents. "
            "If information is not in the context, say so. Be concise and accurate."
        )
        messages.append({"role": "system", "content": system_message})

        # Context message
        context_message = f"Context from documents:\n\n{context}"
        messages.append({"role": "user", "content": context_message})

        # Conversation history
        for msg in request.conversation_history:
            messages.append({"role": msg.role, "content": msg.content})

        # Current query
        messages.append({"role": "user", "content": request.query})

        return messages

    def _format_sources(self, chunks: Sequence[ScoredPoint]) -> list[ChunkSource]:
        """Format chunks into ChunkSource objects."""
        sources = []

        for chunk in chunks:
            payload = chunk.payload or {}
            # ScoredPoint from query_points has a score attribute
            score = getattr(chunk, "score", 0.0)
            sources.append(
                ChunkSource(
                    document_id=payload.get("document_id", ""),
                    chunk_id=str(payload.get("chunk_id", "")),
                    text=payload.get("text", ""),
                    similarity_score=score,
                    page_number=payload.get("page_number"),
                    section_title=payload.get("section_title"),
                )
            )

        return sources
