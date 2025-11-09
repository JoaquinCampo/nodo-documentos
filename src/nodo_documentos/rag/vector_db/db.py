from functools import lru_cache
from typing import Sequence
from uuid import uuid4

from loguru import logger
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    ScoredPoint,
    VectorParams,
)

from nodo_documentos.rag.parsing.models import ParsedDocument
from nodo_documentos.rag.vector_db.settings import settings
from nodo_documentos.services.models import ClinicalDocumentChunk


class VectorDB:
    """Wrapper around Qdrant for indexing and searching documents."""

    def __init__(self) -> None:
        self._settings = settings
        self._collection = self._settings.collection_name
        self._client = self._build_client()

    def _build_client(self) -> QdrantClient:
        logger.debug(
            "Connecting to Qdrant host={host} grpc_port={port} prefer_grpc={pref_grpc}",
            host=self._settings.host,
            port=self._settings.grpc_port,
            pref_grpc=self._settings.prefer_grpc,
        )
        return QdrantClient(
            host=self._settings.host,
            grpc_port=self._settings.grpc_port,
            prefer_grpc=self._settings.prefer_grpc,
            timeout=self._settings.timeout_seconds,
            api_key=self._settings.api_key,
        )

    # ------------------------------------------------------------------
    # Collection management
    # ------------------------------------------------------------------
    def ensure_collection(self) -> None:
        """Create the target collection if it doesn't already exist."""

        collection_exists = self._client.collection_exists(self._collection)

        if not collection_exists:
            logger.info(
                "Creating Qdrant collection={collection} size={size}",
                collection=self._collection,
                size=self._settings.vector_size,
            )
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(
                    size=self._settings.vector_size,
                    distance=Distance.COSINE,
                ),
            )

        self._ensure_payload_indexes()

    def _ensure_payload_indexes(self) -> None:
        """Create payload indexes for fields used in queries."""
        try:
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name="document_id",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.debug("Created index on document_id")

        except Exception as e:
            logger.debug(f"Index on document_id may already exist: {e}")

        try:
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name="document_name",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.debug("Created index on document_name")

        except Exception as e:
            logger.debug(f"Index on document_name may already exist: {e}")

        try:
            self._client.create_payload_index(
                collection_name=self._collection,
                field_name="health_user_ci",
                field_schema=PayloadSchemaType.KEYWORD,
            )
            logger.debug("Created index on health_user_ci")

        except Exception as e:
            logger.debug(f"Index on health_user_ci may already exist: {e}")

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    def index_document(
        self,
        document: ParsedDocument,
        chunks: Sequence[ClinicalDocumentChunk],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        """Upsert chunk embeddings for a document into Qdrant."""

        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings must have the same length")

        # Ensure collection exists before indexing
        self.ensure_collection()

        points = [
            self._build_point(chunk=chunk, vector=vector)
            for chunk, vector in zip(chunks, embeddings, strict=True)
        ]

        logger.info(
            "Upserting {count} chunks for document={document}",
            count=len(points),
            document=document.document_name,
        )
        self._client.upsert(
            collection_name=self._collection,
            points=points,
        )

    def _build_point(
        self,
        chunk: ClinicalDocumentChunk,
        vector: Sequence[float],
    ) -> PointStruct:
        point_id = str(uuid4())
        payload = chunk.model_dump()

        return PointStruct(id=point_id, vector=list(vector), payload=payload)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------
    def search(
        self,
        embedding: Sequence[float],
        *,
        limit: int = 10,
        health_user_ci: str,
        document_id: str | None = None,
    ) -> list[ScoredPoint]:
        """Search the vector store using a query embedding with ownership filtering."""

        # Ensure collection and indexes exist before searching
        self.ensure_collection()

        # Build filter with ownership constraints
        filter_conditions = [
            FieldCondition(
                key="health_user_ci", match=MatchValue(value=health_user_ci)
            ),
        ]

        # Add document filter if specified
        if document_id:
            filter_conditions.append(
                FieldCondition(key="document_id", match=MatchValue(value=document_id))
            )

        query_filter = Filter(must=filter_conditions)  # type: ignore

        response = self._client.query_points(
            collection_name=self._collection,
            query=list(embedding),
            limit=limit,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=False,
        )
        return list(response.points)

    def document_exists(self, document_name: str) -> bool:
        """Return True if any chunks for the given document are stored."""

        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_name", match=MatchValue(value=document_name)
                )
            ]
        )

        results = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=query_filter,
            limit=1,
        )
        points, _ = results
        return True if points else False

    def get_chunks_for_document(
        self,
        document_id: str,
        limit: int = 10,
    ) -> list[ScoredPoint]:
        """Return chunks for a specific document by document_id."""

        query_filter = Filter(
            must=[
                FieldCondition(key="document_id", match=MatchValue(value=document_id))
            ]
        )

        results = self._client.scroll(
            collection_name=self._collection,
            scroll_filter=query_filter,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        points, _ = results
        return list(points)  # type: ignore


@lru_cache
def get_vector_db() -> VectorDB:
    """Return a cached vector database instance."""

    return VectorDB()
