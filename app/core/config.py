from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Finance Copilot API"
    api_version: str = "v1"
    database_url: str = "sqlite:///./finance_copilot.db"

    jwt_issuer: str = "finance-copilot"
    jwt_audience: str = "finance-copilot-client"
    jwks_url: str | None = None
    jwt_secret_key: str | None = "dev-secret"
    jwt_algorithm: str = "HS256"


@lru_cache
def get_settings() -> Settings:
    return Settings()
