"""Base settings shared by services."""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseServiceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")
    rootline_env: Literal["local", "gke", "ci", "ci-e2e", "eval", "test"] = "local"
    log_level: str = "INFO"
    database_url: str | None = None
