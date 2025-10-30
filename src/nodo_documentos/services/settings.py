from pydantic_settings import BaseSettings, SettingsConfigDict


class ServicesSettings(BaseSettings):
    """Holds configuration for service integrations."""

    hcen_api_base_url: str = "http://localhost:8080/practico/api"

    model_config = SettingsConfigDict(env_prefix="SERVICES_", extra="ignore")


services_settings = ServicesSettings()
