import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from nodo_documentos.api.middleware import APIKeyMiddleware


@pytest.mark.asyncio
async def test_api_key_middleware_enforces_header():
    app = FastAPI()

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

    app.add_middleware(APIKeyMiddleware, api_key="secret", header_name="x-api-key")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ping")
        assert response.status_code == 401

        response = await client.get("/ping", headers={"x-api-key": "wrong"})
        assert response.status_code == 401

        response = await client.get("/ping", headers={"x-api-key": "secret"})
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
