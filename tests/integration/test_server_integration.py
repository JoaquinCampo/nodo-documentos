"""
Integration test against a running server.

This test makes real HTTP requests to a running API server to verify
the complete end-to-end flow works in a production-like environment.

Usage:
    1. Start the server: uv run uvicorn nodo_documentos.app:app --host 0.0.0.0 --port 8000
    2. Run this test: uv run pytest tests/integration/test_server_integration.py -v -s

The test will:
    1. Upload sample.pdf to S3 via presigned URL
    2. Create document record (triggers RAG indexing)
    3. Wait for indexing to complete
    4. Test chat queries with various scenarios
"""

import asyncio
import os
from pathlib import Path

import httpx
import pytest

from nodo_documentos.rag.inference.settings import settings as cerebras_settings
from nodo_documentos.rag.vector_db.db import get_vector_db


# Base URL for the running server
BASE_URL = os.getenv("TEST_SERVER_URL", "http://localhost:8000")
API_BASE = f"{BASE_URL}/api"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_server_chat_flow():
    """
    End-to-end integration test against running server.

    Tests the complete flow: Upload → Index → Chat

    Prerequisites:
        - Server must be running: uv run uvicorn nodo_documentos.app:app --host 0.0.0.0 --port 8000
        - CEREBRAS_API_KEY environment variable must be set
        - sample.pdf must exist in project root
    """
    # Skip if Cerebras API key is not configured
    if not cerebras_settings.api_key:
        pytest.skip(
            "CEREBRAS_API_KEY not set - skipping server integration test. "
            "Set CEREBRAS_API_KEY environment variable to run this test."
        )

    # Load sample.pdf
    script_dir = Path(__file__).parent.parent.parent
    sample_pdf_path = script_dir / "sample.pdf"

    if not sample_pdf_path.exists():
        pytest.skip(f"sample.pdf not found at {sample_pdf_path}")

    pdf_size_kb = sample_pdf_path.stat().st_size / 1024
    print(f"\n🚀 Starting server integration test...")
    print(f"📄 Using PDF: {sample_pdf_path.name} ({pdf_size_kb:.2f} KB)")
    print(f"🌐 Server URL: {BASE_URL}\n")

    # Read PDF content
    with open(sample_pdf_path, "rb") as f:
        pdf_content = f.read()

    async with httpx.AsyncClient(timeout=120.0) as client:
        # Check if server is running
        try:
            health_check = await client.get(f"{BASE_URL}/docs", timeout=5.0)
            if health_check.status_code not in [200, 404]:  # 404 is OK for /docs
                pytest.skip(
                    f"Server appears to be down or unreachable at {BASE_URL}. "
                    f"Status: {health_check.status_code}"
                )
        except httpx.ConnectError:
            pytest.skip(
                f"Cannot connect to server at {BASE_URL}. "
                "Make sure the server is running: "
                "uv run uvicorn nodo_documentos.app:app --host 0.0.0.0 --port 8000"
            )
        # Step 1: Get presigned upload URL
        print("📤 Step 1: Getting presigned upload URL...")
        clinic_id = "11111111-2222-3333-4444-555555555555"
        upload_response = await client.post(
            f"{API_BASE}/documents/upload-url",
            json={
                "file_name": "sample.pdf",
                "content_type": "application/pdf",
                "clinic_id": clinic_id,
            },
        )
        assert upload_response.status_code == 201, (
            f"Failed to get upload URL: {upload_response.status_code} - {upload_response.text}"
        )
        upload_data = upload_response.json()
        upload_url = upload_data["upload_url"]
        s3_url = upload_data["s3_url"]
        print(f"✅ Got upload URL: {upload_data['object_key']}\n")

        # Step 2: Upload PDF to S3
        print("📤 Step 2: Uploading PDF to S3...")
        upload_http_response = await client.put(
            upload_url,
            content=pdf_content,
            headers={"Content-Type": "application/pdf"},
        )
        assert upload_http_response.status_code in [200, 201], (
            f"Failed to upload PDF: {upload_http_response.status_code}"
        )
        print("✅ PDF uploaded to S3\n")

        # Step 3: Create document record (triggers background RAG indexing)
        print("📝 Step 3: Creating document record (triggers RAG indexing)...")
        doc_payload = {
            "created_by": "12345678",
            "health_user_ci": "87654321",
            "clinic_id": clinic_id,
            "s3_url": s3_url,
        }

        doc_response = await client.post(
            f"{API_BASE}/documents",
            json=doc_payload,
        )
        assert doc_response.status_code == 201, (
            f"Failed to create document: {doc_response.status_code} - {doc_response.text}"
        )
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

        # Step 5: Test chat query (filter by document_id to avoid old chunks)
        print("💬 Step 5: Testing chat query...")
        chat_payload = {
            "query": "What is this document about?",
            "conversation_history": [],
            "health_user_ci": "87654321",
            "document_id": str(doc_id),  # Filter by the document we just created
        }

        chat_response = await client.post(
            f"{API_BASE}/chat",
            json=chat_payload,
        )
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

        follow_up_response = await client.post(
            f"{API_BASE}/chat",
            json=follow_up_payload,
        )
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

        filtered_response = await client.post(
            f"{API_BASE}/chat",
            json=filtered_payload,
        )
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

        # Step 8: Test clinical history endpoint
        print("📋 Step 8: Testing clinical history endpoint...")
        history_response = await client.get(
            f"{API_BASE}/clinical-history/87654321",
            params={
                "health_worker_ci": "12345678",
                "clinic_id": clinic_id,
            },
        )
        assert history_response.status_code == 200
        history_data = history_response.json()

        # Verify document is in the list
        doc_ids = [doc["doc_id"] for doc in history_data]
        assert str(doc_id) in doc_ids, f"Document {doc_id} not found in clinical history"
        print(f"✅ Clinical history returned {len(history_data)} documents\n")

        print("🎉 Server integration test completed successfully!")
        print(f"   Document: {doc_id}")
        print(
            f"   Total chunks indexed: {len(vector_db.get_chunks_for_document(str(doc_id), limit=1000))}"
        )
        print(f"   Chat queries tested: 3")
        print(f"   API endpoints tested: 4")

