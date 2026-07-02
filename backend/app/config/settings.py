from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "Sentinel AI Backend"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Security
    jwt_secret_key: str = "change-me-in-production-use-at-least-32-random-bytes"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Database
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel_ai"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Logging
    log_level: str = "INFO"

    # AI fallback - direct provider calls when Continuum/the Smart Gateway is
    # too slow for a live demo. Lives here (not treated as Continuum SDK
    # config) because it's Sentinel's own resilience decision, not something
    # the Continuum SDK itself knows about.
    continuum_fallback_timeout_seconds: int = 30
    openai_api_key: str | None = None
    openai_fallback_model: str = "gpt-4o-mini"
    anthropic_api_key: str | None = None
    anthropic_fallback_model: str = "claude-haiku-4-5-20251001"

    # Continuum content-hash cache (app/continuum/cache.py) - identical
    # instructions+input+schema returns the prior result instead of paying
    # for another AI call. 24h matches the PR-review freshness convention.
    continuum_cache_ttl_seconds: int = 86_400

    # Slack incident notifications (app/integrations/slack/) - an Incoming
    # Webhook URL, not a bot token, so no OAuth/scopes setup is needed. When
    # unset, IncidentService simply skips notification (same "degrade
    # quietly" convention as the AWS cost integration).
    slack_webhook_url: str | None = None

    # Health monitor (app/services/health_monitor.py) - background poller
    # that detects a collapsed container and drives it through
    # IncidentService (create -> analyze -> Slack alert) with no human
    # action needed. Disable for environments where auto-opening incidents
    # isn't wanted (e.g. a shared Docker host running unrelated containers).
    health_monitor_enabled: bool = True
    health_monitor_interval_seconds: int = 20

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
