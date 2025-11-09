from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from nodo_documentos.api.router import api_router
from nodo_documentos.db.models import Base
from nodo_documentos.db.session import get_async_session


@pytest_asyncio.fixture
async def async_session() -> AsyncIterator[AsyncSession]:
    """
    Provides a fresh in-memory SQLite DB and async session per test.

    Using SQLite keeps tests lightweight while still exercising the SQLAlchemy
    ORM logic used by our repositories.
    """

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        future=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
        await session.rollback()

    await engine.dispose()


@pytest_asyncio.fixture
async def test_app(async_session: AsyncSession) -> AsyncIterator[FastAPI]:
    """FastAPI app instance bound to the ephemeral SQLite session."""

    app = FastAPI(title="Documentos Clinicos", version="0.1.0")
    
    @app.get("/")
    async def root():
        return {"status": "ok", "service": "nodo-documentos"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    # Include router but skip API key middleware for tests
    app.include_router(api_router, prefix="/api")

    async def _override_session():
        yield async_session

    app.dependency_overrides[get_async_session] = _override_session

    yield app

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(test_app: FastAPI) -> AsyncIterator[AsyncClient]:
    """HTTP client backed by the test FastAPI app."""

    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client
