"""Application settings, loaded from environment variables and an optional `.env` file."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    project_title: str = "JobBoard"
    project_version: str = "1.0.0"

    # Full SQLAlchemy URL. Defaults to a local SQLite file so the app runs with zero setup;
    # set DATABASE_URL to PostgreSQL (e.g. via docker compose) for anything real.
    database_url: str = "sqlite:///./jobboard.db"

    # JWT signing. ALWAYS override SECRET_KEY outside local development.
    secret_key: str = Field(default="dev-only-insecure-secret-change-me", min_length=16)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Set to true when served over HTTPS so the auth cookie is marked Secure.
    cookie_secure: bool = False

    seed_demo_data: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
