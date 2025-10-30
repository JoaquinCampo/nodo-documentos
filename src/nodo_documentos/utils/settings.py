from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class S3Settings(BaseSettings):
    """Holds configuration required to interact with S3-compatible storage."""

    bucket_name: str = "nodo-documentos"
    region_name: str = "us-east-1"
    endpoint_url: str | None = None
    presigned_expiration_seconds: int = 900

    model_config = SettingsConfigDict(env_prefix="S3_", extra="ignore")

    @field_validator("endpoint_url", mode="before")
    @classmethod
    def _empty_string_as_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


class APISettings(BaseSettings):
    """Controls API key validation for external clients."""

    key: str | None = None
    header_name: str = "x-api-key"

    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")


s3_settings = S3Settings()
api_settings = APISettings()

__all__ = ["APISettings", "S3Settings", "api_settings", "s3_settings"]
