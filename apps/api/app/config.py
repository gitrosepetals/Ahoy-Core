from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "A-hoy API"
    environment: str = "development"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/ahoy"

    jwt_secret: str = "dev-change-me-ahoy-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_ttl_hours: int = 48
    magic_link_ttl_minutes: int = 30

    # When true, magic-link SMS is logged/returned instead of sent via Twilio
    auth_dev_mode: bool = True
    ship_app_base_url: str = "http://localhost:3000"
    crew_app_base_url: str = "http://localhost:3000"

    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    cors_origins: str = "http://localhost:3000,capacitor://localhost,http://localhost"


@lru_cache
def get_settings() -> Settings:
    return Settings()
