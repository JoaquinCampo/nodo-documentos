from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from nodo_documentos.rag.chunking.models import Chunk
from nodo_documentos.rag.parsing.models import DocumentMetadata, PageInfo, ParsedDocument
from nodo_documentos.db.models import Document
from nodo_documentos.services.models import ClinicalDocumentChunk
from nodo_documentos.services.rag_service import RAGService


@pytest.mark.asyncio
async def test_document_creation_triggers_rag_indexing(
    async_client, test_app, monkeypatch
):
    """Test that creating a document triggers RAG indexing in background."""
    # Mock S3 download
    mock_pdf_bytes = b"%PDF-1.4 fake pdf content"
    monkeypatch.setattr(
        "nodo_documentos.services.rag_service.download_from_s3",
        lambda _: mock_pdf_bytes,
    )

    # Mock PDF parser
    mock_parsed_doc = ParsedDocument(
        id="test-doc-id",
        paper_name="test_document",
        file_path=Path("/tmp/test.pdf"),
        text="Test document content",
        sections=[],
        page_info=[],
        metadata=DocumentMetadata(pages_processed=1, ocr_model="test-model"),
    )
    mock_parser = MagicMock()
    mock_parser.parse_pdf = MagicMock(return_value=mock_parsed_doc)

    # Mock chunker
    mock_chunks = [
        Chunk(
            chunk_id=0,
            paper_id="test-doc-id",
            paper_name="test_document",
            text="Test chunk content",
            section_title=None,
            page_number=1,
            token_count=5,
        )
    ]
    mock_chunker = MagicMock()
    mock_chunker.chunk_document = MagicMock(return_value=mock_chunks)

    # Mock encoder
    mock_embeddings = [[0.1, 0.2, 0.3] * 512]  # 1536-dim vector
    mock_encoder = MagicMock()
    mock_encoder.embed_many = MagicMock(return_value=mock_embeddings)

    # Mock vector DB
    mock_vector_db = MagicMock()
    mock_vector_db.index_document = MagicMock()

    # Create RAG service with mocks
    rag_service_instance = RAGService(
        mock_vector_db, mock_parser, mock_chunker, mock_encoder
    )

    # Override the dependency in the test app
    from nodo_documentos.api.dependencies import rag_service

    test_app.dependency_overrides[rag_service] = lambda: rag_service_instance

    # Create document
    payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_id": "11111111-2222-3333-4444-555555555555",
        "s3_url": "s3://bucket/test-doc.pdf",
    }

    response = await async_client.post("/api/documents", json=payload)
    assert response.status_code == 201
    created = response.json()
    doc_id = created["doc_id"]

    # Wait for background task to execute
    import asyncio

    await asyncio.sleep(1.0)

    # Verify RAG pipeline was called
    assert mock_parser.parse_pdf.called
    assert mock_chunker.chunk_document.called
    assert mock_encoder.embed_many.called
    assert mock_vector_db.index_document.called

    # Verify clinical chunks were created with ownership metadata
    call_args = mock_vector_db.index_document.call_args
    parsed_doc_arg, clinical_chunks_arg, embeddings_arg = call_args[0]

    assert len(clinical_chunks_arg) == 1
    clinical_chunk = clinical_chunks_arg[0]
    assert isinstance(clinical_chunk, ClinicalDocumentChunk)
    assert clinical_chunk.document_id == doc_id
    assert clinical_chunk.health_user_ci == "87654321"
    assert clinical_chunk.clinic_id == "11111111-2222-3333-4444-555555555555"
    assert clinical_chunk.created_by == "12345678"

    # Cleanup
    test_app.dependency_overrides.pop(rag_service, None)


@pytest.mark.asyncio
async def test_rag_indexing_failure_does_not_break_document_creation(
    async_client, monkeypatch
):
    """Test that RAG indexing failures don't prevent document creation."""
    # Mock S3 download to fail
    monkeypatch.setattr(
        "nodo_documentos.services.rag_service.download_from_s3",
        lambda _: (_ for _ in ()).throw(Exception("S3 download failed")),
    )

    # Create document
    payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_id": "11111111-2222-3333-4444-555555555555",
        "s3_url": "s3://bucket/test-doc.pdf",
    }

    response = await async_client.post("/api/documents", json=payload)
    # Document should still be created successfully
    assert response.status_code == 201
    created = response.json()
    assert created["doc_id"]


@pytest.mark.asyncio
async def test_rag_service_index_document_integration():
    """Test RAG service index_document method directly."""
    from nodo_documentos.db.models import Document
    from nodo_documentos.services.rag_service import RAGService

    # Create mock components
    mock_vector_db = MagicMock()
    mock_parser = MagicMock()
    mock_chunker = MagicMock()
    mock_encoder = MagicMock()

    # Setup mocks
    mock_pdf_bytes = b"%PDF-1.4 fake pdf content"
    mock_parsed_doc = ParsedDocument(
        id="test-doc-id",
        paper_name="test_document",
        file_path=Path("/tmp/test.pdf"),
        text="Test document content",
        sections=[],
        page_info=[],
        metadata=DocumentMetadata(pages_processed=1, ocr_model="test-model"),
    )
    mock_chunks = [
        Chunk(
            chunk_id=0,
            paper_id="test-doc-id",
            paper_name="test_document",
            text="Test chunk",
            section_title=None,
            page_number=1,
            token_count=2,
        )
    ]
    mock_embeddings = [[0.1] * 1536]

    mock_parser.parse_pdf.return_value = mock_parsed_doc
    mock_chunker.chunk_document.return_value = mock_chunks
    mock_encoder.embed_many.return_value = mock_embeddings

    # Create service
    service = RAGService(mock_vector_db, mock_parser, mock_chunker, mock_encoder)

    # Create test document
    from datetime import datetime

    document = Document(
        doc_id=UUID("11111111-2222-3333-4444-555555555555"),
        created_by="12345678",
        health_user_ci="87654321",
        clinic_id="11111111-2222-3333-4444-555555555555",
        s3_url="s3://bucket/test.pdf",
        created_at=datetime.now(),
    )

    # Mock S3 download
    with patch("nodo_documentos.services.rag_service.download_from_s3") as mock_download:
        mock_download.return_value = mock_pdf_bytes

        # Index document
        await service.index_document(document)

        # Verify pipeline execution
        assert mock_download.called
        assert mock_parser.parse_pdf.called
        assert mock_chunker.chunk_document.called
        assert mock_encoder.embed_many.called
        assert mock_vector_db.index_document.called

        # Verify clinical chunks have ownership metadata
        call_args = mock_vector_db.index_document.call_args
        _, clinical_chunks, _ = call_args[0]

        assert len(clinical_chunks) == 1
        assert clinical_chunks[0].document_id == "11111111-2222-3333-4444-555555555555"
        assert clinical_chunks[0].health_user_ci == "87654321"
        assert clinical_chunks[0].clinic_id == "11111111-2222-3333-4444-555555555555"
        assert clinical_chunks[0].created_by == "12345678"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_rag_indexing_stores_chunks_in_qdrant(monkeypatch):
    """
    Integration test that verifies chunks are actually stored in Qdrant.

    This test uses real Qdrant, OpenAI embeddings, but mocks S3 and PDF parsing
    to avoid external API dependencies.
    """
    import os

    # Skip if Qdrant is not configured
    if not os.getenv("qdrant_host"):
        pytest.skip("Qdrant not configured - skipping integration test")

    from datetime import datetime
    from uuid import UUID

    from nodo_documentos.rag.chunking.chunker import get_chunker
    from nodo_documentos.rag.encoding.encoder import get_encoder
    from nodo_documentos.rag.parsing.parser import get_parser
    from nodo_documentos.rag.vector_db.db import get_vector_db
    from nodo_documentos.services.rag_service import RAGService

    # Create real RAG service components
    vector_db = get_vector_db()
    pdf_parser = get_parser()
    pdf_chunker = get_chunker()
    encoder = get_encoder()

    # Mock S3 download with a minimal PDF
    mock_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 0\ntrailer\n<<\n/Root 1 0 R\n>>\n%%EOF"
    monkeypatch.setattr(
        "nodo_documentos.services.rag_service.download_from_s3",
        lambda _: mock_pdf_bytes,
    )

    # Mock PDF parser to return a simple parsed document
    mock_parsed_doc = ParsedDocument(
        id="test-integration-doc",
        paper_name="test_integration",
        file_path=Path("/tmp/test.pdf"),
        text="# Test Document\n\nThis is a test document for integration testing.\n\n## Section 1\n\nSome content here.",
        sections=[],
        page_info=[
            PageInfo(page_number=1, char_start=0, char_end=100)
        ],
        metadata=DocumentMetadata(pages_processed=1, ocr_model="test"),
    )
    monkeypatch.setattr(pdf_parser, "parse_pdf", lambda _: mock_parsed_doc)

    # Create RAG service
    service = RAGService(vector_db, pdf_parser, pdf_chunker, encoder)

    # Create test document
    test_doc_id = UUID("99999999-9999-9999-9999-999999999999")
    document = Document(
        doc_id=test_doc_id,
        created_by="12345678",
        health_user_ci="87654321",
        clinic_id="11111111-2222-3333-4444-555555555555",
        s3_url="s3://bucket/test-integration.pdf",
        created_at=datetime.now(),
    )

    # Index document
    await service.index_document(document)

    # Wait a bit for async operations
    import asyncio

    await asyncio.sleep(2.0)

    # Verify chunks are stored in Qdrant
    chunks = vector_db.get_chunks_for_document(str(test_doc_id))

    assert len(chunks) > 0, "No chunks found in Qdrant for the document"
    print(f"✅ Found {len(chunks)} chunks in Qdrant for document {test_doc_id}")

    # Verify ownership metadata
    for chunk_point in chunks:
        payload = chunk_point.payload
        assert payload["document_id"] == str(test_doc_id)
        assert payload["health_user_ci"] == "87654321"
        assert payload["clinic_id"] == "11111111-2222-3333-4444-555555555555"
        assert payload["created_by"] == "12345678"
        assert "text" in payload
        assert "chunk_id" in payload
        print(f"✅ Chunk {payload['chunk_id']} has correct ownership metadata")

    # Cleanup: remove test chunks (skip if index not available)
    try:
        vector_db.remove_document("test_integration")
    except Exception as e:
        # Cleanup failure is OK - chunks are stored, just can't delete without index
        print(f"⚠️  Cleanup skipped (index required): {e}")
