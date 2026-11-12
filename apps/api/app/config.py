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

    # Owner notifications (0.8.0). SMS goes out only when Twilio is configured AND auth_dev_mode
    # is off; push only when FCM is configured. Otherwise notifications are logged (dev).
    notify_link_ttl_hours: int = 48  # Story 1.1: SMS deep link valid for 48 hours
    queue_reminder_hours_before: int = 48  # CL-02: remind 48h before the queue expires
    fcm_project_id: str = ""
    fcm_service_account_file: str = ""  # path to Google service-account JSON

    # Encrypts per-client integration secrets at rest (integration_credentials). Change in prod.
    credentials_encryption_key: str = "dev-change-me-ahoy-credentials-key"

    # Publishing (0.9.0). Without an API key, approved posts are "published" in dev mode
    # (fake external id) so the local flow completes.
    ayrshare_api_key: str = ""
    publish_max_attempts: int = 3

    # Background jobs (0.9.0): run `python -m app.worker`, or set true to run the loop
    # inside the API process (single-instance deployments / local dev).
    embedded_worker: bool = False

    # Reviews (0.11.0). Google OAuth app for Business Profile (scope business.manage); the
    # redirect URI must be registered in Google Cloud and point at /integrations/google/callback.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/api/v1/integrations/google/callback"
    yelp_api_key: str = ""  # Yelp Fusion (read-only: Yelp has no reply API)

    # Billing (0.13.0). Price ids of the three monthly tiers in Stripe.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_harbor: str = ""
    stripe_price_cruiser: str = ""
    stripe_price_flagship: str = ""

    llm_dev_mode: bool = True
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    # File storage (1.2.0): "local" = UPLOAD_DIR served at /uploads; "supabase" = Supabase Storage
    # (required in production, where the API host's disk is ephemeral). The bucket must be public.
    storage_backend: str = "local"
    supabase_url: str = ""  # https://<project-ref>.supabase.co
    supabase_service_key: str = ""  # service_role key, server-side only
    supabase_bucket: str = "ahoy-media"
    upload_dir: str = "uploads"
    public_api_base_url: str = "http://127.0.0.1:8000"

    # Observability (0.15.0)
    log_format: str = "text"  # "json" in production
    log_level: str = "INFO"
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0

    cors_origins: str = "http://localhost:3000,capacitor://localhost,http://localhost"


@lru_cache
def get_settings() -> Settings:
    return Settings()
