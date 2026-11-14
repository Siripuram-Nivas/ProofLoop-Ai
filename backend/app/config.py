from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SECRET = "dev-only-insecure-secret-change-me"


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _load_dotenv() -> None:
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    env: str = os.getenv("PROOFLOOP_ENV", "development")
    secret: str = os.getenv("PROOFLOOP_SECRET", DEFAULT_SECRET)
    db_path: Path = field(
        default_factory=lambda: Path(os.getenv("PROOFLOOP_DB", str(BASE_DIR / "data" / "proofloop.db")))
    )
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "PROOFLOOP_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        ).split(",")
        if origin.strip()
    )
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "").strip()
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    gemini_search_model: str = (
        os.getenv("GEMINI_SEARCH_MODEL", "").strip()
        or os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
    )
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "").strip()
    # No default on purpose: an unset model must surface as "not configured",
    # never as a guessed model name.
    openai_model: str = os.getenv("OPENAI_MODEL", "").strip()
    google_search_enabled: bool = _env_bool("GOOGLE_SEARCH_ENABLED")
    ai_live_calls_enabled: bool = _env_bool("PROOFLOOP_AI_LIVE_CALLS_ENABLED")

    # Engine selection. Empty means "keep the existing deterministic path".
    claim_engine: str = os.getenv("PROOFLOOP_CLAIM_ENGINE", "").strip().lower()
    analysis_engine: str = os.getenv("PROOFLOOP_ANALYSIS_ENGINE", "").strip().lower()
    review_engine: str = os.getenv("PROOFLOOP_REVIEW_ENGINE", "").strip().lower()
    second_review_engine: str = os.getenv("PROOFLOOP_SECOND_REVIEW_ENGINE", "").strip().lower()
    research_engine: str = os.getenv("PROOFLOOP_RESEARCH_ENGINE", "").strip().lower()

    ai_timeout_seconds: float = float(os.getenv("PROOFLOOP_AI_TIMEOUT_SECONDS", "20"))
    search_timeout_seconds: float = float(os.getenv("PROOFLOOP_SEARCH_TIMEOUT_SECONDS", "25"))
    ai_max_retries: int = int(os.getenv("PROOFLOOP_AI_MAX_RETRIES", "2"))
    ai_max_input_chars: int = int(os.getenv("PROOFLOOP_AI_MAX_INPUT_CHARS", "12000"))
    ai_max_output_tokens: int = int(os.getenv("PROOFLOOP_AI_MAX_OUTPUT_TOKENS", "1200"))

    # Automatic provider failover between OpenAI and Gemini.
    ai_auto_fallback_enabled: bool = _env_bool("AI_AUTO_FALLBACK_ENABLED", True)
    ai_provider_order: tuple[str, ...] = tuple(
        name.strip().lower()
        for name in os.getenv("AI_PROVIDER_ORDER", "openai,gemini").split(",")
        if name.strip()
    )
    ai_fallback_max_attempts: int = max(
        1, int(os.getenv("AI_FALLBACK_MAX_ATTEMPTS", "2"))
    )
    ai_provider_cooldown_seconds: float = float(
        os.getenv("AI_PROVIDER_COOLDOWN_SECONDS", "300")
    )

    research_provider: str = os.getenv("PROOFLOOP_RESEARCH", "wikipedia").strip()
    momen_graphql_url: str = os.getenv(
        "MOMEN_GRAPHQL_URL",
        "https://villa.momen.app/zero/vXL04vkvze2/api/graphql-v2",
    ).strip()
    momen_subscription_url: str = os.getenv(
        "MOMEN_SUBSCRIPTION_URL",
        "wss://villa.momen.app/zero/vXL04vkvze2/api/graphql-subscription",
    ).strip()
    # Server-only. Used for reads because Logged-in User has no table grants.
    momen_admin_token: str = os.getenv("MOMEN_ADMIN_TOKEN", "").strip()
    momen_timeout_seconds: float = float(os.getenv("MOMEN_TIMEOUT_SECONDS", "15"))

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def uses_default_secret(self) -> bool:
        return self.secret == DEFAULT_SECRET or len(self.secret) < 24


settings = Settings()
