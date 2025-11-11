from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from nodo_documentos.db.settings import db_settings

# Lazy initialization: engine and sessionmaker are created on first access
_engine: AsyncEngine | None = None
_AsyncSessionLocal: async_sessionmaker[AsyncSession] | None = None


def _create_async_engine() -> AsyncEngine:
    """Initialize the async SQLAlchemy engine."""
    url = db_settings.async_database_url
    if not url:
        raise ValueError(
            "ASYNC_DATABASE_URL environment variable is required but not set"
        )

    if not url.startswith(("postgresql+asyncpg://", "postgresql://")):
        raise ValueError(
            f"Invalid database URL format. "
            f"Expected postgresql+asyncpg:// or postgresql://, got: {url[:30]}..."
        )

    # Use NullPool for serverless environments (Vercel/Lambda)
    # This prevents connection reuse across different event loops
    # Each request gets a fresh connection that's properly scoped
    engine = create_async_engine(
        url,
        echo=db_settings.sqlalchemy_echo,
        poolclass=NullPool,  # Disable connection pooling for serverless
    )
    logger.info("Async database engine initialized")
    return engine


def get_engine() -> AsyncEngine:
    """Return the database engine, creating it lazily on first access."""
    global _engine
    if _engine is None:
        _engine = _create_async_engine()
    return _engine


def get_async_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """Return the async sessionmaker, creating it lazily on first access."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            autoflush=False,
        )
    return _AsyncSessionLocal


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session with commit / rollback."""

    sessionmaker = get_async_sessionmaker()
    async with sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
