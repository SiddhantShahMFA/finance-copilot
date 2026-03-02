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

    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_timeout_seconds: float = 10.0

    rate_limit_enabled: bool = True
    rate_limit_requests: int = 30
    rate_limit_window_seconds: int = 60
    rate_limit_path_prefixes: str = "/v1/copilot/query,/v1/simulations/run,/v1/family"
    observability_latency_window: int = 1000


@lru_cache
def get_settings() -> Settings:
    return Settings()
