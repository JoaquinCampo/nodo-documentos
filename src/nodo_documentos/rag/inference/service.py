from functools import lru_cache
from typing import Any, Sequence

from cerebras.cloud.sdk import Cerebras
from loguru import logger

from nodo_documentos.rag.inference.settings import settings


class CerebrasInferenceService:
    """Service for generating LLM responses using Cerebras Inference API."""

    def __init__(self) -> None:
        self._client = Cerebras(api_key=settings.api_key)
        self._model = settings.model

    def generate(
        self,
        messages: Sequence[dict[str, Any]],
        *,
        temperature: float = 0.3,
    ) -> str:
        """
        Generate a response using Cerebras Inference API.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature

        Returns:
            Generated response text

        Raises:
            Exception: If API call fails
        """
        logger.debug(
            f"Calling Cerebras API: model={self._model}, messages={len(messages)}"
        )

        try:
            chat_completion = self._client.chat.completions.create(
                messages=list(messages),
                model=self._model,
                temperature=temperature,
            )

            response_text = chat_completion.choices[0].message.content  # type: ignore
            logger.debug(f"Received response: {len(response_text)} characters")

            return response_text

        except Exception as e:
            logger.error(
                f"Failed to generate response from Cerebras API: {e}",
                exc_info=True,
            )
            raise


@lru_cache
def get_inference_service() -> CerebrasInferenceService:
    """Return a cached Cerebras inference service instance."""
    return CerebrasInferenceService()
