from functools import lru_cache
from typing import Sequence

from loguru import logger
from openai import OpenAI

from nodo_documentos.rag.encoding.settings import settings


class EmbeddingEncoder:
    def __init__(self):
        self._model = settings.embedding_model
        self._client = OpenAI(api_key=settings.openai_api_key)

    def embed(self, text: str) -> list[float]:
        """Return the embedding vector for a single text input."""

        if not text:
            raise ValueError("text must not be empty")

        logger.debug("Embedding text")

        response = self._client.embeddings.create(model=self._model, input=[text])
        vector = response.data[0].embedding
        return list(vector)

    def embed_many(
        self,
        texts: Sequence[str],
        *,
        batch_size: int = 64,
    ) -> list[list[float]]:
        """
        Return embedding vectors for multiple text inputs.

        Args:
            texts: Iterable of input strings.
            batch_size: Maximum number of strings to send per API call.

        Returns:
            List of embedding vectors aligned with the input order.
        """
        texts = list(texts)
        if not texts:
            return []

        logger.debug(f"Embedding {len(texts)} texts (batch_size={batch_size})")

        vectors: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            response = self._client.embeddings.create(
                model=self._model,
                input=batch,
            )
            vectors.extend(list(item.embedding) for item in response.data)

        return vectors


@lru_cache
def get_encoder() -> EmbeddingEncoder:
    """Return a cached encoder instance."""

    return EmbeddingEncoder()
