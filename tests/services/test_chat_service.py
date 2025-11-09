from unittest.mock import MagicMock

import pytest

from nodo_documentos.api.schemas import ChatRequest, Message
from nodo_documentos.rag.encoding.encoder import EmbeddingEncoder
from nodo_documentos.rag.inference.service import CerebrasInferenceService
from nodo_documentos.rag.vector_db.db import VectorDB
from nodo_documentos.services.chat_service import ChatService


@pytest.mark.asyncio
async def test_chat_with_chunks_found():
    """Test chat service with successful chunk retrieval."""
    # Setup mocks
    mock_vector_db = MagicMock(spec=VectorDB)
    mock_encoder = MagicMock(spec=EmbeddingEncoder)
    mock_inference = MagicMock(spec=CerebrasInferenceService)

    # Mock query embedding
    mock_encoder.embed.return_value = [0.1] * 1536

    # Mock vector search results - use MagicMock for ScoredPoint
    mock_chunk1 = MagicMock()
    mock_chunk1.score = 0.9
    mock_chunk1.payload = {
        "document_id": "doc-123",
        "chunk_id": "0",
        "text": "Patient has diabetes",
        "page_number": 1,
        "section_title": "Diagnosis",
    }

    mock_chunk2 = MagicMock()
    mock_chunk2.score = 0.85
    mock_chunk2.payload = {
        "document_id": "doc-123",
        "chunk_id": "1",
        "text": "Medications: Metformin 500mg",
        "page_number": 2,
        "section_title": "Medications",
    }

    mock_vector_db.search.return_value = [mock_chunk1, mock_chunk2]

    # Mock LLM response
    mock_inference.generate.return_value = "The patient has diabetes and is taking Metformin."

    # Create service
    service = ChatService(mock_vector_db, mock_encoder, mock_inference)

    # Create request
    request = ChatRequest(
        query="What medications is the patient taking?",
        health_user_ci="87654321",
    )

    # Call chat
    response = await service.chat(request)

    # Verify
    assert response.answer == "The patient has diabetes and is taking Metformin."
    assert len(response.sources) == 2
    assert response.sources[0].document_id == "doc-123"
    assert response.sources[0].chunk_id == "0"
    assert response.sources[0].text == "Patient has diabetes"
    assert response.sources[0].similarity_score == 0.9
    assert response.sources[0].page_number == 1

    # Verify calls
    mock_encoder.embed.assert_called_once_with(request.query)
    mock_vector_db.search.assert_called_once_with(
        embedding=[0.1] * 1536,
        limit=10,
        health_user_ci="87654321",
        document_id=None,
    )
    assert mock_inference.generate.called


@pytest.mark.asyncio
async def test_chat_with_document_id_filter():
    """Test chat service with specific document_id filter."""
    mock_vector_db = MagicMock(spec=VectorDB)
    mock_encoder = MagicMock(spec=EmbeddingEncoder)
    mock_inference = MagicMock(spec=CerebrasInferenceService)

    mock_encoder.embed.return_value = [0.1] * 1536

    mock_chunk = MagicMock()
    mock_chunk.score = 0.9
    mock_chunk.payload = {
        "document_id": "doc-123",
        "chunk_id": "0",
        "text": "Test content",
    }
    mock_vector_db.search.return_value = [mock_chunk]
    mock_inference.generate.return_value = "Answer"

    service = ChatService(mock_vector_db, mock_encoder, mock_inference)

    request = ChatRequest(
        query="Test query",
        health_user_ci="87654321",
        document_id="11111111-2222-3333-4444-555555555555",
    )

    response = await service.chat(request)

    assert response.answer == "Answer"
    mock_vector_db.search.assert_called_once_with(
        embedding=[0.1] * 1536,
        limit=10,
        health_user_ci="87654321",
        document_id="11111111-2222-3333-4444-555555555555",
    )


@pytest.mark.asyncio
async def test_chat_no_chunks_found():
    """Test chat service when no chunks are found."""
    mock_vector_db = MagicMock(spec=VectorDB)
    mock_encoder = MagicMock(spec=EmbeddingEncoder)
    mock_inference = MagicMock(spec=CerebrasInferenceService)

    mock_encoder.embed.return_value = [0.1] * 1536
    mock_vector_db.search.return_value = []

    service = ChatService(mock_vector_db, mock_encoder, mock_inference)

    request = ChatRequest(
        query="Test query",
        health_user_ci="87654321",
    )

    response = await service.chat(request)

    assert response.answer == "I couldn't find relevant information in the documents."
    assert len(response.sources) == 0
    assert not mock_inference.generate.called


@pytest.mark.asyncio
async def test_chat_with_conversation_history():
    """Test chat service includes conversation history in messages."""
    mock_vector_db = MagicMock(spec=VectorDB)
    mock_encoder = MagicMock(spec=EmbeddingEncoder)
    mock_inference = MagicMock(spec=CerebrasInferenceService)

    mock_encoder.embed.return_value = [0.1] * 1536

    mock_chunk = MagicMock()
    mock_chunk.score = 0.9
    mock_chunk.payload = {
        "document_id": "doc-123",
        "chunk_id": "0",
        "text": "Test content",
    }
    mock_vector_db.search.return_value = [mock_chunk]
    mock_inference.generate.return_value = "Answer"

    service = ChatService(mock_vector_db, mock_encoder, mock_inference)

    request = ChatRequest(
        query="Follow-up question",
        conversation_history=[
            Message(role="user", content="First question"),
            Message(role="assistant", content="First answer"),
        ],
        health_user_ci="87654321",
    )

    await service.chat(request)

    # Verify messages include history
    call_args = mock_inference.generate.call_args
    messages = call_args.kwargs.get("messages") or call_args.args[0]

    assert len(messages) == 5  # system + context + 2 history + query
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"  # context
    assert messages[2]["role"] == "user"  # history
    assert messages[3]["role"] == "assistant"  # history
    assert messages[4]["role"] == "user"  # query
    assert messages[4]["content"] == "Follow-up question"
