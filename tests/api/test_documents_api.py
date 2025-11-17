from urllib.parse import quote

import pytest

from nodo_documentos.utils.s3_utils import PresignedUrl
from nodo_documentos.utils.settings import s3_settings


@pytest.mark.asyncio
async def test_create_document(async_client, monkeypatch):
    expected_presigned_url = "https://s3.amazonaws.com/bucket/doc-1?signature=test"
    monkeypatch.setattr(
        "nodo_documentos.utils.s3_utils.generate_presigned_get_url",
        lambda **kwargs: PresignedUrl(url=expected_presigned_url, expires_in=600),
    )

    payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_name": "Test Clinic",
        "s3_url": "s3://bucket/doc-1",
    }

    response = await async_client.post("/api/documents", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["health_user_ci"] == payload["health_user_ci"]
    assert created["doc_id"]
    # content_url should be presigned HTTPS URL
    assert created["content_url"] == expected_presigned_url


@pytest.mark.asyncio
async def test_create_document_with_hcen_aliases(async_client, monkeypatch):
    """Test that HCEN field names (health_worker_ci, content_url) work correctly."""
    expected_presigned_url = "https://s3.amazonaws.com/bucket/doc-2?signature=abc123"
    monkeypatch.setattr(
        "nodo_documentos.utils.s3_utils.generate_presigned_get_url",
        lambda **kwargs: PresignedUrl(url=expected_presigned_url, expires_in=600),
    )

    payload = {
        "health_worker_ci": "12345678",  # Alias for created_by
        "health_user_ci": "87654321",
        "clinic_name": "Test Clinic",
        "content_url": "s3://bucket/doc-2",  # Alias for s3_url
        "title": "Test Document",
    }

    response = await async_client.post("/api/documents", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["health_user_ci"] == payload["health_user_ci"]
    # Response should use HCEN aliases (health_worker_ci, content_url)
    assert created["health_worker_ci"] == payload["health_worker_ci"]
    # content_url should be a presigned HTTPS URL, not the internal S3 URI
    assert created["content_url"] == expected_presigned_url
    assert created["content_url"].startswith("https://")
    assert created["doc_id"]


@pytest.mark.asyncio
async def test_create_presigned_upload_url(async_client, monkeypatch):
    fake_uuid = "11111111-2222-3333-4444-555555555555"
    clinic_name = "Test Clinic"
    expected_key = f"{clinic_name}/{fake_uuid}/document.pdf"
    expected_url = "https://example.com/upload"
    monkeypatch.setattr(
        "nodo_documentos.api.routes.documents.uuid4",
        lambda: fake_uuid,
    )
    monkeypatch.setattr(
        "nodo_documentos.api.routes.documents.generate_presigned_put_url",
        lambda **_: PresignedUrl(url=expected_url, expires_in=600),
    )

    response = await async_client.post(
        "/api/documents/upload-url",
        json={
            "file_name": "document.pdf",
            "content_type": "application/pdf",
            "clinic_name": clinic_name,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["object_key"] == expected_key
    # S3 URI should have URL-encoded spaces in the key
    expected_s3_url = f"s3://{s3_settings.bucket_name}/{quote(expected_key, safe='/')}"
    assert payload["s3_url"] == expected_s3_url
    assert payload["upload_url"] == expected_url
    assert payload["expires_in_seconds"] == 600


@pytest.mark.asyncio
async def test_presigned_upload_url_sanitizes_filename(async_client, monkeypatch):
    fake_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    clinic_name = "Another Clinic"
    monkeypatch.setattr(
        "nodo_documentos.api.routes.documents.uuid4",
        lambda: fake_uuid,
    )
    captured: dict[str, str] = {}

    def _fake_presign(**kwargs):
        captured["key"] = kwargs["key"]
        return PresignedUrl(url="https://example.com", expires_in=900)

    monkeypatch.setattr(
        "nodo_documentos.api.routes.documents.generate_presigned_put_url",
        _fake_presign,
    )

    response = await async_client.post(
        "/api/documents/upload-url",
        json={
            "file_name": " nested/path/report.pdf ",
            "content_type": None,
            "clinic_name": clinic_name,
        },
    )

    assert response.status_code == 201
    assert captured["key"].endswith("/report.pdf")


@pytest.mark.asyncio
async def test_content_url_is_presigned_https_url(async_client, monkeypatch):
    """Test that content_url is automatically converted to presigned HTTPS URL."""
    s3_uri = "s3://test-bucket/clinic/doc.pdf"
    expected_presigned_url = "https://s3.amazonaws.com/test-bucket/clinic/doc.pdf?X-Amz-Signature=xyz"
    
    monkeypatch.setattr(
        "nodo_documentos.utils.s3_utils.generate_presigned_get_url",
        lambda **kwargs: PresignedUrl(url=expected_presigned_url, expires_in=600),
    )

    payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_name": "Test Clinic",
        "s3_url": s3_uri,
    }

    response = await async_client.post("/api/documents", json=payload)
    assert response.status_code == 201
    created = response.json()
    
    # content_url should be the presigned HTTPS URL, not the internal S3 URI
    assert created["content_url"] == expected_presigned_url
    assert created["content_url"].startswith("https://")
    assert s3_uri not in created["content_url"]  # Should not contain s3://


@pytest.mark.asyncio
async def test_content_url_is_none_when_no_s3_url(async_client):
    """Test that content_url is None when document has no S3 URL."""
    payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_name": "Test Clinic",
        "title": "Text-only document",
        "content": "This is a text document without file upload",
    }

    response = await async_client.post("/api/documents", json=payload)
    assert response.status_code == 201
    created = response.json()
    
    assert created["content_url"] is None


@pytest.mark.asyncio
async def test_clinical_history_returns_presigned_urls(async_client, monkeypatch):
    """Test that clinical history endpoint returns presigned URLs for content_url."""
    expected_presigned_url = "https://s3.amazonaws.com/bucket/doc.pdf?signature=test123"
    monkeypatch.setattr(
        "nodo_documentos.utils.s3_utils.generate_presigned_get_url",
        lambda **kwargs: PresignedUrl(url=expected_presigned_url, expires_in=600),
    )

    # Create a document first
    create_response = await async_client.post(
        "/api/documents",
        json={
            "created_by": "12345678",
            "health_user_ci": "87654321",
            "clinic_name": "Test Clinic",
            "s3_url": "s3://bucket/doc.pdf",
        },
    )
    assert create_response.status_code == 201

    # Fetch clinical history
    response = await async_client.get("/api/clinical-history/87654321")
    assert response.status_code == 200
    documents = response.json()
    
    assert len(documents) == 1
    assert documents[0]["content_url"] == expected_presigned_url
    assert documents[0]["content_url"].startswith("https://")
