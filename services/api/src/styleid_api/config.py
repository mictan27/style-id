"""Runtime settings.

Every setting reads from the environment with the ``STYLEID_`` prefix
(``STYLEID_JWT_SECRET`` ...). The handful of variables that ``.env.example``
lists un-prefixed are accepted in both spellings; the prefixed one wins:

* ``DATABASE_URL`` / ``STYLEID_DATABASE_URL``
* ``ANTHROPIC_API_KEY`` / ``STYLEID_ANTHROPIC_API_KEY``
* ``CHART_EXTRACTION_MODEL`` / ``STYLEID_CHART_EXTRACTION_MODEL``
* ``BLOB_BUCKET`` / ``STYLEID_BLOB_BUCKET``
"""

from __future__ import annotations

from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ExtractionRunnerKind = Literal["inline", "queue"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="STYLEID_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="sqlite+pysqlite:///./styleid-dev.db",
        validation_alias=AliasChoices("STYLEID_DATABASE_URL", "DATABASE_URL"),
    )
    #: Create tables with ``Base.metadata.create_all`` at startup (SQLite dev only).
    auto_create_tables: bool = False

    # --- auth -------------------------------------------------------------
    #: Accept ``X-Dev-User: <handle>`` and mint ``dev:<handle>`` users. Never in production.
    dev_auth_enabled: bool = True
    #: When set, dev auth additionally requires ``X-Dev-Secret`` to match.
    dev_auth_secret: str | None = None
    #: The iOS bundle id: the ``aud`` claim of Apple identity tokens.
    apple_client_id: str = "id.style.app"
    apple_issuer: str = "https://appleid.apple.com"
    apple_jwks_url: str = "https://appleid.apple.com/auth/keys"
    apple_jwks_ttl_seconds: int = 3600
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_issuer: str = "style.id"
    jwt_ttl_seconds: int = 60 * 60 * 24 * 30

    # --- extraction -------------------------------------------------------
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("STYLEID_ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
    )
    chart_extraction_model: str = Field(
        default="claude-opus-5-5",
        validation_alias=AliasChoices("STYLEID_CHART_EXTRACTION_MODEL", "CHART_EXTRACTION_MODEL"),
    )
    blob_bucket: str = Field(
        default="styleid-dev",
        validation_alias=AliasChoices("STYLEID_BLOB_BUCKET", "BLOB_BUCKET"),
    )
    #: ``inline`` runs extraction inside the request; ``queue`` defers a procrastinate job.
    extraction_runner: ExtractionRunnerKind = "inline"

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


def get_settings() -> Settings:
    return Settings()
