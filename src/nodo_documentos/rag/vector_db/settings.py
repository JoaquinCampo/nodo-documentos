from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for connecting to Qdrant."""

    host: str = ""
    grpc_port: int = 6334
    api_key: str = ""

    prefer_grpc: bool = True
    collection_name: str = "clinical-documents"
    vector_size: int = 1536
    timeout_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="qdrant_",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
