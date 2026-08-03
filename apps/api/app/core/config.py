from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "case_management.db"
DEFAULT_DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    database_url: str = f"sqlite:///{DEFAULT_DATABASE_PATH.as_posix()}"
    jwt_secret: str = "development-only-secret"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    environment: str = "development"
    attachment_max_bytes: int = 10 * 1024 * 1024
    attachment_allowed_types: str = "application/pdf,image/png,image/jpeg,text/plain"
    attachment_directory: Path = PROJECT_ROOT / "data" / "attachments"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
