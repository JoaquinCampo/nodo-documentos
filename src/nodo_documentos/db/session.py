from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from nodo_documentos.db.settings import db_settings


def _create_async_engine() -> AsyncEngine:
    """Initialize the async SQLAlchemy engine."""

    engine = create_async_engine(
        db_settings.async_database_url,
        echo=db_settings.sqlalchemy_echo,
    )
    logger.info("Async database engine initialized")
    return engine


engine: AsyncEngine = _create_async_engine()
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
    autoflush=False,
)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async session with commit / rollback."""

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
