"""
Integration test for the complete chat flow with RAG.

This test verifies:
1. Document creation via API
2. Background RAG indexing (S3 download → PDF parse → chunk → embed → store)
3. Chat query with vector search and LLM inference
4. Response generation with source citations
"""

import asyncio
import os
from pathlib import Path

import pytest

from nodo_documentos.rag.inference.settings import settings as cerebras_settings
from nodo_documentos.rag.vector_db.db import get_vector_db


@pytest.mark.asyncio
@pytest.mark.integration
async def test_complete_chat_flow_with_rag(async_client, test_app):
    """
    End-to-end integration test: Create document → Index → Chat.

    Uses real sample.pdf and verifies the complete RAG pipeline.
    """
    # Skip if Cerebras API key is not configured
    if not cerebras_settings.api_key:
        pytest.skip(
            "CEREBRAS_API_KEY not set - skipping chat integration test. "
            "Set CEREBRAS_API_KEY environment variable to run this test."
        )

    print("\n🚀 Starting complete chat flow integration test...\n")

    # Load sample.pdf
    script_dir = Path(__file__).parent.parent.parent
    sample_pdf_path = script_dir / "sample.pdf"

    if not sample_pdf_path.exists():
        pytest.skip(f"sample.pdf not found at {sample_pdf_path}")

    pdf_size_kb = sample_pdf_path.stat().st_size / 1024
    print(f"📄 Using PDF: {sample_pdf_path.name} ({pdf_size_kb:.2f} KB)\n")

    # Read PDF content
    with open(sample_pdf_path, "rb") as f:
        pdf_content = f.read()

    # Step 1: Get presigned upload URL
    print("📤 Step 1: Getting presigned upload URL...")
    clinic_id = "11111111-2222-3333-4444-555555555555"
    upload_response = await async_client.post(
        "/api/documents/upload-url",
        json={
            "file_name": "sample.pdf",
            "content_type": "application/pdf",
            "clinic_id": clinic_id,
        },
    )
    assert upload_response.status_code == 201
    upload_data = upload_response.json()
    upload_url = upload_data["upload_url"]
    s3_url = upload_data["s3_url"]
    print(f"✅ Got upload URL: {upload_data['object_key']}\n")

    # Step 2: Upload PDF to S3
    print("📤 Step 2: Uploading PDF to S3...")
    import httpx

    async with httpx.AsyncClient() as http_client:
        upload_http_response = await http_client.put(
            upload_url,
            content=pdf_content,
            headers={"Content-Type": "application/pdf"},
        )
        assert upload_http_response.status_code in [200, 201]
    print("✅ PDF uploaded to S3\n")

    # Step 3: Create document record (triggers background RAG indexing)
    print("📝 Step 3: Creating document record (triggers RAG indexing)...")
    doc_payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_id": clinic_id,
        "s3_url": s3_url,
    }

    doc_response = await async_client.post("/api/documents", json=doc_payload)
    assert doc_response.status_code == 201
    doc_data = doc_response.json()
    doc_id = doc_data["doc_id"]
    print(f"✅ Document created: {doc_id}\n")

    # Step 4: Wait for RAG indexing to complete
    print("⏳ Step 4: Waiting for RAG indexing to complete...")
    print("   (S3 download → PDF parse → chunk → embed → store in Qdrant)\n")

    vector_db = get_vector_db()
    max_wait = 120  # Wait up to 2 minutes for real PDF processing
    waited = 0
    chunks_found = False

    while waited < max_wait:
        await asyncio.sleep(5)
        waited += 5

        chunks = vector_db.get_chunks_for_document(str(doc_id), limit=1)
        if chunks:
            chunks_found = True
            all_chunks = vector_db.get_chunks_for_document(str(doc_id), limit=1000)
            print(f"✅ Found {len(all_chunks)} chunks after {waited} seconds!\n")
            break

        print(f"   ... still waiting ({waited}s) ...")

    assert chunks_found, (
        f"No chunks found after {max_wait} seconds - indexing may have failed"
    )

    # Step 5: Test chat query
    print("💬 Step 5: Testing chat query...")
    chat_payload = {
        "query": "What is this document about?",
        "conversation_history": [],
        "health_user_ci": "87654321",
    }

    chat_response = await async_client.post("/api/chat", json=chat_payload)
    if chat_response.status_code != 200:
        print(f"❌ Chat request failed with status {chat_response.status_code}")
        print(f"   Response: {chat_response.text}")
        print(f"\n   Note: This may indicate:")
        print(f"   - Invalid or missing CEREBRAS_API_KEY")
        print(f"   - Network connectivity issues")
        print(f"   - Cerebras API service issues")
        pytest.fail(f"Chat API call failed: {chat_response.text}")
    chat_data = chat_response.json()

    print(f"✅ Chat response received!\n")
    print(f"   Answer: {chat_data['answer'][:200]}...")
    print(f"   Sources: {len(chat_data['sources'])} chunks\n")

    # Verify response structure
    assert "answer" in chat_data
    assert "sources" in chat_data
    assert len(chat_data["answer"]) > 0
    assert len(chat_data["sources"]) > 0

    # Verify sources have correct metadata
    for source in chat_data["sources"][:3]:  # Check first 3 sources
        assert source["document_id"] == str(doc_id)
        assert "chunk_id" in source
        assert "text" in source
        assert "similarity_score" in source
        assert source["similarity_score"] > 0

    print("✅ Source metadata verified\n")

    # Step 6: Test chat with conversation history
    print("💬 Step 6: Testing chat with conversation history...")
    follow_up_payload = {
        "query": "Can you tell me more details?",
        "conversation_history": [
            {"role": "user", "content": "What is this document about?"},
            {"role": "assistant", "content": chat_data["answer"]},
        ],
        "health_user_ci": "87654321",
    }

    follow_up_response = await async_client.post("/api/chat", json=follow_up_payload)
    assert follow_up_response.status_code == 200
    follow_up_data = follow_up_response.json()

    assert len(follow_up_data["answer"]) > 0
    print(
        f"✅ Follow-up response received: {len(follow_up_data['answer'])} characters\n"
    )

    # Step 7: Test chat with specific document filter
    print("💬 Step 7: Testing chat with document_id filter...")
    filtered_payload = {
        "query": "Summarize the key points",
        "health_user_ci": "87654321",
        "document_id": str(doc_id),
    }

    filtered_response = await async_client.post("/api/chat", json=filtered_payload)
    assert filtered_response.status_code == 200
    filtered_data = filtered_response.json()

    assert len(filtered_data["answer"]) > 0
    assert len(filtered_data["sources"]) > 0

    # Verify all sources are from the specified document
    for source in filtered_data["sources"]:
        assert source["document_id"] == str(doc_id)

    print(
        f"✅ Filtered query returned {len(filtered_data['sources'])} sources from document {doc_id}\n"
    )

    print("🎉 Integration test completed successfully!")
    print(f"   Document: {doc_id}")
    print(
        f"   Total chunks indexed: {len(vector_db.get_chunks_for_document(str(doc_id), limit=1000))}"
    )
    print(f"   Chat queries tested: 3")
