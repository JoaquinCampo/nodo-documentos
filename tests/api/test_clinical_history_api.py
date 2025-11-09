from __future__ import annotations

import pytest


async def _create_document(async_client) -> dict:
    payload = {
        "created_by": "12345678",
        "health_user_ci": "87654321",
        "clinic_id": "11111111-2222-3333-4444-555555555555",
        "s3_url": "s3://bucket/doc-1",
    }
    response = await async_client.post("/api/documents", json=payload)
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_fetch_clinical_history_returns_documents(async_client):
    created = await _create_document(async_client)

    response = await async_client.get(
        f"/api/clinical-history/{created['health_user_ci']}",
        params={
            "health_worker_ci": "11112222",
            "clinic_id": "11111111-2222-3333-4444-555555555555",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["doc_id"] == created["doc_id"]


@pytest.mark.asyncio
async def test_fetch_clinical_history_empty_for_nonexistent_user(async_client):
    """Test that fetching clinical history for a user with no documents returns empty list."""
    response = await async_client.get(
        "/api/clinical-history/99999999",
        params={
            "health_worker_ci": "11112222",
            "clinic_id": "11111111-2222-3333-4444-555555555555",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data == []
