import pytest

from nodo_documentos.utils.s3_utils import PresignedUrl
from nodo_documentos.utils.settings import s3_settings


@pytest.mark.asyncio
async def test_create_document(async_client):
    payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_id": "11111111-2222-3333-4444-555555555555",
        "s3_url": "s3://bucket/doc-1",
    }

    response = await async_client.post("/api/documents", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["health_user_ci"] == payload["health_user_ci"]
    assert created["doc_id"]


@pytest.mark.asyncio
async def test_create_presigned_upload_url(async_client, monkeypatch):
    fake_uuid = "11111111-2222-3333-4444-555555555555"
    clinic_id = "11111111-2222-3333-4444-555555555555"
    expected_key = f"{clinic_id}/{fake_uuid}/document.pdf"
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
            "clinic_id": clinic_id,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["object_key"] == expected_key
    assert payload["s3_url"] == f"s3://{s3_settings.bucket_name}/{expected_key}"
    assert payload["upload_url"] == expected_url
    assert payload["expires_in_seconds"] == 600


@pytest.mark.asyncio
async def test_presigned_upload_url_sanitizes_filename(async_client, monkeypatch):
    fake_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    clinic_id = "bbbbbbbb-1111-2222-3333-cccccccccccc"
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
            "clinic_id": clinic_id,
        },
    )

    assert response.status_code == 201
    assert captured["key"].endswith("/report.pdf")
