from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    app_title: str = "Geo Analytics API"
    app_version: str = "1.0.0"

    # CORS
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_credentials: bool = False
    cors_allow_methods: List[str] = field(default_factory=lambda: ["*"])
    cors_allow_headers: List[str] = field(default_factory=lambda: ["*"])

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"


def load_settings() -> Settings:
    """Build settings from environment variables with sensible defaults."""
    origins_raw = os.environ.get("CORS_ORIGINS", "*")
    origins = [o.strip() for o in origins_raw.split(",") if o.strip()]

    return Settings(
        app_title=os.environ.get("APP_TITLE", Settings.app_title),
        app_version=os.environ.get("APP_VERSION", Settings.app_version),
        cors_origins=origins,
        cors_allow_credentials=os.environ.get("CORS_ALLOW_CREDENTIALS", "false").lower()
        == "true",
        host=os.environ.get("HOST", Settings.host),
        port=int(os.environ.get("PORT", Settings.port)),
        log_level=os.environ.get("LOG_LEVEL", Settings.log_level),
    )


settings = load_settings()
