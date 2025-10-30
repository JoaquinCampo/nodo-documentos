from __future__ import annotations

import pytest

from nodo_documentos.api.dependencies import authorization_service
from nodo_documentos.api.schemas import AuthorizationDecision
from nodo_documentos.services.authorization_service import AuthorizationService


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
async def test_fetch_clinical_history_returns_documents(async_client, test_app):
    created = await _create_document(async_client)

    class _AllowAuthorization(AuthorizationService):
        async def can_view_clinical_history(self, **_: str):  # type: ignore[override]
            return AuthorizationDecision(allowed=True, reason="ALLOWED")

    test_app.dependency_overrides[authorization_service] = lambda: _AllowAuthorization()

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
async def test_fetch_clinical_history_denied(async_client, test_app):
    await _create_document(async_client)

    class _DenyAuthorization(AuthorizationService):
        async def can_view_clinical_history(self, **_: str):  # type: ignore[override]
            return AuthorizationDecision(allowed=False, reason="DENIED")

    test_app.dependency_overrides[authorization_service] = lambda: _DenyAuthorization()

    response = await async_client.get(
        "/api/clinical-history/87654321",
        params={
            "health_worker_ci": "11112222",
            "clinic_id": "11111111-2222-3333-4444-555555555555",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "DENIED"
