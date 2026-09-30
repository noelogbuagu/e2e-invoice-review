from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class AppConfig:
    database_url: str = "sqlite:///./data/documents.db"
    upload_dir: Path = Path("./data/uploads")
    max_upload_bytes: int = 4 * 1024 * 1024


APP_CONFIG = AppConfig()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    azure_document_intelligence_endpoint: str
    azure_document_intelligence_key: str
    azure_openai_endpoint: str
    azure_openai_deployment: str
    azure_openai_api_key: str
    allowed_origin: str = "http://localhost:5173"
    nylas_api_key: str = ""
    nylas_api_uri: str = "https://api.us.nylas.com"
    nylas_grant_id: str = ""
    webhook_secret: str = ""
    server_url: str = ""
    app_access_password: str = ""
    app_session_secret: str = ""
    frontend_dist_dir: str = ""

    @model_validator(mode="after")
    def session_secret_required(self) -> Self:
        if self.app_access_password and not self.app_session_secret:
            raise ValueError("Set APP_SESSION_SECRET when APP_ACCESS_PASSWORD is set.")
        return self

    @property
    def auth_enabled(self) -> bool:
        return bool(self.app_access_password)

    def resolve_frontend_dist(self) -> Path | None:
        if self.frontend_dist_dir:
            path = Path(self.frontend_dist_dir)
            if not path.is_dir():
                raise ValueError(f"FRONTEND_DIST_DIR does not exist: {path}")
            return path
        candidate = BACKEND_ROOT.parent / "frontend" / "dist"
        if candidate.is_dir():
            return candidate
        return None


@lru_cache
def get_settings() -> Settings:
    return Settings()  # pyright: ignore[reportCallIssue]
