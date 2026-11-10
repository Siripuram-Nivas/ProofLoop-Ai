from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SECRET = "dev-only-insecure-secret-change-me"


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
    research_provider: str = os.getenv("PROOFLOOP_RESEARCH", "wikipedia").strip()

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def uses_default_secret(self) -> bool:
        return self.secret == DEFAULT_SECRET or len(self.secret) < 24


settings = Settings()
