from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from nodo_documentos.api.dependencies import chat_service
from nodo_documentos.api.schemas import ChatRequest, ChatResponse
from nodo_documentos.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def chat(
    request: ChatRequest,
    service: ChatService = Depends(chat_service),
) -> ChatResponse:
    """
    Process a chat query against patient documents using RAG.

    Searches document chunks using vector similarity, assembles context,
    and generates a response using Cerebras inference.

    **Request Body:**
    - `query`: The user's question
    - `health_user_ci`: Patient's CI
    - `conversation_history`: Previous messages in the conversation
    - `document_id`: Optional UUID to limit search to a specific document

    **Response:**
    - `answer`: LLM-generated answer based on retrieved document chunks
    - `sources`: List of document chunks used to generate the answer, with similarity scores

    **Example Request:**
    ```json
    {
      "query": "What is the patient's diagnosis?",
      "health_user_ci": "87654321",
      "conversation_history": [
        {"role": "user", "content": "Previous question"},
        {"role": "assistant", "content": "Previous answer"}
      ]
    }
    ```
    """
    try:
        return await service.chat(request)

    except ValueError as e:
        # No chunks found or other validation errors
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        # Cerebras API errors or other unexpected errors
        # Use % formatting to avoid issues with gRPC error messages containing {}
        logger.error("Chat endpoint error: %s", str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response. Please try again.",
        )
