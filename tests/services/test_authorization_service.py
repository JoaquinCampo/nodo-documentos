import pytest
from httpx import ASGITransport, AsyncClient

from nodo_documentos.mock_hcen.app import app as mock_hcen_app
from nodo_documentos.services.authorization_service import AuthorizationService


@pytest.fixture
def _patch_httpx(monkeypatch):
    """
    Route AuthorizationService HTTP calls to the in-process mock HCEN app.
    """

    transport = ASGITransport(app=mock_hcen_app)
    original_async_client = AsyncClient

    def _client_factory(*_, **__):
        return original_async_client(transport=transport, base_url="http://mock-hcen")

    monkeypatch.setattr(
        "nodo_documentos.services.authorization_service.httpx.AsyncClient",
        _client_factory,
    )


@pytest.mark.asyncio
async def test_authorization_allows_when_mock_returns_200(
    _patch_httpx,
    monkeypatch,
):
    monkeypatch.setenv("MOCK_HCEN_DECISION", "allow")
    service = AuthorizationService(base_url="http://mock-hcen/practico/api")

    decision = await service.can_view_clinical_history(
        health_user_ci="87654321",
        health_worker_ci="11112222",
        clinic_id="11111111-2222-3333-4444-555555555555",
    )

    assert decision.allowed is True
    assert decision.reason == "mock-allow"


@pytest.mark.asyncio
async def test_authorization_denies_when_mock_returns_403(
    _patch_httpx,
    monkeypatch,
):
    monkeypatch.setenv("MOCK_HCEN_DECISION", "deny")
    service = AuthorizationService(base_url="http://mock-hcen/practico/api")

    decision = await service.can_view_clinical_history(
        health_user_ci="87654321",
        health_worker_ci="11112222",
        clinic_id="11111111-2222-3333-4444-555555555555",
    )

    assert decision.allowed is False
    assert decision.reason == "mock-deny"


@pytest.mark.asyncio
async def test_authorization_handles_unexpected_status(
    _patch_httpx,
    monkeypatch,
):
    monkeypatch.setenv("MOCK_HCEN_DECISION", "error")
    service = AuthorizationService(base_url="http://mock-hcen/practico/api")

    decision = await service.can_view_clinical_history(
        health_user_ci="87654321",
        health_worker_ci="11112222",
        clinic_id="11111111-2222-3333-4444-555555555555",
    )

    assert decision.allowed is False
    assert decision.reason == "unexpected-status"
