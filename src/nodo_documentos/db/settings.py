from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """Centralizes DB configuration for the async SQLAlchemy engine."""

    async_database_url: str = Field(
        default="",
        description="PostgreSQL connection URL (postgresql+asyncpg://...)",
    )
    sqlalchemy_echo: bool = False

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


db_settings = DatabaseSettings()
