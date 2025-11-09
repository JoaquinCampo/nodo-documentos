from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for Cerebras Inference API."""

    api_key: str = Field(default="", description="Cerebras API key from environment")
    model: str = Field(default="gpt-oss-120b", description="Model name for inference")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="cerebras_",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
