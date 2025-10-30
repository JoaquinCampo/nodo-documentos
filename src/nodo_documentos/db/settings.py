from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Centralizes DB configuration for the async SQLAlchemy engine."""

    async_database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/nodo_documentos"
    )
    sqlalchemy_echo: bool = False


db_settings = DatabaseSettings()
