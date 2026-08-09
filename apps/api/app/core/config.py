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
    seed_demo_users: bool = False
    directory_mode: str = "none"
    entra_tenant_id: str | None = None
    entra_client_id: str | None = None
    entra_client_secret: str | None = None
    active_directory_server: str | None = None
    active_directory_base_dn: str | None = None
    active_directory_bind_user: str | None = None
    active_directory_bind_password: str | None = None
    active_directory_use_ssl: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
