from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "ASO Compass API"
    app_version: str = "0.1.0"
    app_env: Literal["local", "demo", "test"] = "local"
    database_url: str = "sqlite:///./aso_compass_local.db"
    frontend_origins: Annotated[list[str], NoDecode] = [
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ]
    db_pool_size: int = Field(default=3, ge=1, le=10)
    db_max_overflow: int = Field(default=2, ge=0, le=10)
    db_pool_timeout_seconds: float = Field(default=15.0, ge=1.0, le=60.0)
    open_targets_url: str = "https://api.platform.opentargets.org/api/v4/graphql"
    clinical_trials_url: str = "https://clinicaltrials.gov/api/v2/studies"
    http_timeout_seconds: float = 60.0
    http_retry_total: int = 4
    max_active_runs: int = 1
    max_queued_runs: int = 10
    create_run_rate_limit_per_minute: int = 12
    run_worker_enabled: bool = True
    ai_enabled: bool = False
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-6-luna"
    ai_max_output_tokens: int = Field(default=1800, ge=256, le=4000)
    ai_timeout_seconds: float = Field(default=45.0, ge=5.0, le=120.0)
    ai_rate_limit_per_minute: int = Field(default=6, ge=1, le=60)

    @field_validator("frontend_origins", mode="before")
    @classmethod
    def split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
