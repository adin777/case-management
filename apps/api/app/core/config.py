from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://case_management:case_management_dev@localhost:5432/case_management"
    jwt_secret: str = "development-only-secret"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    environment: str = "development"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
settings = Settings()
