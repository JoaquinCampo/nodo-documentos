from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for Mistral OCR parsing."""

    mistral_api_key: str = ""
    ocr_model: str = "mistral-ocr-latest"
    include_images_by_default: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
