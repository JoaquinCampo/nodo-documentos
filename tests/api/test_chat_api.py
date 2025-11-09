from unittest.mock import AsyncMock, MagicMock

import pytest

from nodo_documentos.api.schemas import ChatRequest, ChatResponse, ChunkSource, Message


@pytest.mark.asyncio
async def test_chat_endpoint_success(async_client, test_app):
    """Test successful chat endpoint call."""
    # Mock the chat service
    mock_chat_service = MagicMock()
    mock_response = ChatResponse(
        answer="The patient has diabetes.",
        sources=[
            ChunkSource(
                document_id="doc-123",
                chunk_id="0",
                text="Patient has diabetes",
                similarity_score=0.9,
                page_number=1,
                section_title="Diagnosis",
            )
        ],
    )
    mock_chat_service.chat = AsyncMock(return_value=mock_response)

    # Override dependency
    from nodo_documentos.api.dependencies import chat_service

    test_app.dependency_overrides[chat_service] = lambda: mock_chat_service

    # Make request
    payload = {
        "query": "What is the patient's diagnosis?",
        "conversation_history": [],
        "health_user_ci": "87654321",
    }

    response = await async_client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The patient has diabetes."
    assert len(data["sources"]) == 1
    assert data["sources"][0]["document_id"] == "doc-123"

    # Cleanup
    test_app.dependency_overrides.pop(chat_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_validation_error(async_client):
    """Test chat endpoint with invalid request."""
    # Empty query
    payload = {
        "query": "",
        "health_user_ci": "87654321",
    }

    response = await async_client.post("/api/chat", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_endpoint_no_chunks(async_client, test_app):
    """Test chat endpoint when no chunks found."""
    mock_chat_service = MagicMock()
    mock_response = ChatResponse(
        answer="I couldn't find relevant information in the documents.",
        sources=[],
    )
    mock_chat_service.chat = AsyncMock(return_value=mock_response)

    from nodo_documentos.api.dependencies import chat_service

    test_app.dependency_overrides[chat_service] = lambda: mock_chat_service

    payload = {
        "query": "Test query",
        "health_user_ci": "87654321",
    }

    response = await async_client.post("/api/chat", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert "couldn't find" in data["answer"].lower()
    assert len(data["sources"]) == 0

    test_app.dependency_overrides.pop(chat_service, None)


@pytest.mark.asyncio
async def test_chat_endpoint_with_conversation_history(async_client, test_app):
    """Test chat endpoint with conversation history."""
    mock_chat_service = MagicMock()
    mock_response = ChatResponse(
        answer="Follow-up answer",
        sources=[],
    )
    mock_chat_service.chat = AsyncMock(return_value=mock_response)

    from nodo_documentos.api.dependencies import chat_service

    test_app.dependency_overrides[chat_service] = lambda: mock_chat_service

    payload = {
        "query": "Follow-up question",
        "conversation_history": [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ],
        "health_user_ci": "87654321",
    }

    response = await async_client.post("/api/chat", json=payload)

    assert response.status_code == 200
    # Verify history was passed to service
    call_args = mock_chat_service.chat.call_args
    request = call_args[0][0]
    assert len(request.conversation_history) == 2

    test_app.dependency_overrides.pop(chat_service, None)
