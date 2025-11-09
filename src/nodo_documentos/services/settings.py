from pydantic_settings import BaseSettings, SettingsConfigDict


class ServicesSettings(BaseSettings):
    """Holds configuration for service integrations."""

    auto_index_documents: bool = True

    model_config = SettingsConfigDict(env_prefix="SERVICES_", extra="ignore")


services_settings = ServicesSettings()
