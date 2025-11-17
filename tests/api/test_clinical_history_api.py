from __future__ import annotations

import pytest

from nodo_documentos.utils.s3_utils import PresignedUrl


async def _create_document(async_client, monkeypatch) -> dict:
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
    return response.json()


@pytest.mark.asyncio
async def test_fetch_clinical_history_returns_documents(async_client, monkeypatch):
    created = await _create_document(async_client, monkeypatch)

    response = await async_client.get(
        f"/api/clinical-history/{created['health_user_ci']}"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["doc_id"] == created["doc_id"]


@pytest.mark.asyncio
async def test_fetch_clinical_history_empty_for_nonexistent_user(async_client):
    """Test that fetching clinical history for a user with no documents returns empty list."""
    response = await async_client.get("/api/clinical-history/99999999")

    assert response.status_code == 200
    data = response.json()
    assert data == []
