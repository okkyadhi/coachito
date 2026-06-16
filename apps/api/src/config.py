from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://coachito_api:coachito_api@postgres:5432/coachito"
    # Superuser DSN used by /i/{token} (public invite landing) to bypass RLS.
    # Stays unset → falls back to database_url.
    alembic_database_url: str | None = None

    # ── Redis ─────────────────────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"

    # ── Auth ──────────────────────────────────────────────────────
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_access_ttl_minutes: int = 15
    jwt_refresh_ttl_days: int = 30
    google_client_id: str = ""
    # Hide & disable Google OAuth (endpoint returns 404). Magic-link endpoints
    # stay live for invite/recovery flows; the UI hides them via VITE_ flags.
    enable_google_oauth: bool = False
    # Trial window applied to every workspace created via self-signup.
    signup_trial_days: int = 30

    # ── Mail (Mailpit local / Gmail SMTP prod) ────────────────────
    smtp_host: str = "mailpit"
    smtp_port: int = 1025
    smtp_from: str = "noreply@coachito.dev"
    # Empty username → anonymous send (Mailpit). Gmail SMTP needs the full
    # email + an App Password (NOT the account password). See .env.example
    # for setup notes.
    smtp_username: str = ""
    smtp_password: str = ""
    # Implicit TLS (smtps, port 465). True for Gmail port 465.
    smtp_use_tls: bool = False
    # Opportunistic STARTTLS upgrade. True for Gmail port 587.
    smtp_start_tls: bool = False

    # ── URLs ──────────────────────────────────────────────────────
    # Used in outbound emails — the FE host the trainee will land on.
    web_url: str = "http://localhost:5174"

    # ── Storage (MinIO local / R2 prod) ──────────────────────────
    # Internal endpoint used by the API itself (e.g. HEAD after upload).
    s3_endpoint: str = "http://minio:9000"
    # Public endpoint baked into presigned URLs sent to the browser.
    # In dev this differs from s3_endpoint because the browser can't resolve
    # "minio".  In prod they're typically the same (R2 custom domain).
    s3_public_endpoint: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "coachito-dev"

    # ── AI (Gemini draft summaries) ──────────────────────────────
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gemini_timeout_s: float = 12.0

    # ── Runtime ───────────────────────────────────────────────────
    environment: str = "development"

    @field_validator("web_url", "s3_endpoint", "s3_public_endpoint", mode="before")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        # Railway-style env values often include a trailing "/", which made
        # invite links render as "https://host//i/{token}".
        return v.rstrip("/") if isinstance(v, str) else v

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
