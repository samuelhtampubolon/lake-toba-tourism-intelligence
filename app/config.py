"""Centralized configuration management with typed settings and validation."""
import os
import secrets
from pathlib import Path
from typing import Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: Literal["development", "lan", "production"] = "development"
    APP_SECRET_KEY: str = Field(
        default_factory=lambda: secrets.token_urlsafe(48),
        description="Cryptographic secret key for session and CSRF integrity."
    )
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    DATA_DIR: str = str(BASE_DIR / "data")
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'lake_toba.sqlite'}"
    SESSION_COOKIE_NAME: str = "toba_session"
    SESSION_EXPIRE_MINUTES: int = 480
    SESSION_INACTIVITY_MINUTES: int = 60
    COOKIE_SECURE: bool = False
    APP_TIMEZONE: str = "Asia/Jakarta"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB
    MAX_CSV_ROWS: int = 50000

    @field_validator("APP_SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        # Never accept a shipped placeholder. Development receives an ephemeral
        # process-local key; operators must supply an explicit key outside dev.
        env = os.getenv("ENVIRONMENT", "development")
        if env in ("lan", "production"):
            if len(v) < 32 or any(marker in v.lower() for marker in ("default", "change-me", "example")):
                raise ValueError(
                    "APP_SECRET_KEY must be at least 32 characters long and not use default placeholders in LAN/production mode."
                )
        return v

    def model_post_init(self, __context: object) -> None:
        """Create the private runtime directory before SQLite opens its file."""
        path = Path(self.DATA_DIR)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.mkdir(parents=True, exist_ok=True)

    @property
    def data_path(self) -> Path:
        path = Path(self.DATA_DIR)
        if not path.is_absolute():
            path = BASE_DIR / path
        path.mkdir(parents=True, exist_ok=True)
        return path

settings = Settings()
