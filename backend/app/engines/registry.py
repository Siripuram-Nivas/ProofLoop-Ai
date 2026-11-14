from __future__ import annotations

from typing import Any, Optional

from ..config import settings
from . import health
from .base import EngineCall  # re-exported for callers
from .errors import ProviderUnavailable
from .gemini_engine import GeminiEngine
from .google_search_engine import GoogleSearchEngine
from .openai_engine import OpenAIEngine

PROVIDER_IDS = ("openai", "gemini")
ALLOWED_CLAIM = {"deterministic", "openai", "gemini"}
ALLOWED_RESEARCH = {"wikipedia", "google_search"}
ALLOWED_ANALYSIS = {"", "openai", "gemini"}
ALLOWED_REVIEW = {"", "openai", "gemini"}

# Truthful, user-facing state per availability reason. `available` stays the single
# "can be called right now" flag; `state` explains why when it is false.
REASON_STATE = {
    "live_calls_disabled": (
        "disabled",
        "Live provider calls are disabled on the server.",
    ),
    "missing_api_key": ("missing_api_key", "No API key is configured for this provider."),
    "missing_model": ("missing_model", "No model name is configured for this provider."),
    "sdk_missing": ("sdk_missing", "The provider SDK is not installed on the server."),
    "search_disabled": ("search_disabled", "Google Search grounding is disabled."),
}


def is_configured(name: str) -> bool:
    """True only when the provider has everything it needs to be called."""
    if name == "openai":
        return bool(settings.openai_api_key and settings.openai_model)
    if name == "gemini":
        return bool(settings.gemini_api_key and settings.gemini_model)
    if name == "google_search":
        return bool(
            settings.google_search_enabled
            and settings.gemini_api_key
            and settings.gemini_search_model
        )
    return False


def provider_order() -> list[str]:
    """Configured fallback priority, filtered to known providers and de-duplicated."""
    order: list[str] = []
    for raw in settings.ai_provider_order or PROVIDER_IDS:
        name = str(raw).strip().lower()
        if name in PROVIDER_IDS and name not in order:
            order.append(name)
    return order or list(PROVIDER_IDS)


def get_engine(name: str):
    """Build an engine from current settings. Never performs a network call."""
    common = {
        "live_enabled": settings.ai_live_calls_enabled,
        "timeout": settings.ai_timeout_seconds,
        "max_retries": settings.ai_max_retries,
        "max_input_chars": settings.ai_max_input_chars,
        "max_output_tokens": settings.ai_max_output_tokens,
    }
    if name == "openai":
        return OpenAIEngine(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            **common,
        )
    if name == "gemini":
        return GeminiEngine(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model,
            **common,
        )
    if name == "google_search":
        return GoogleSearchEngine(
            api_key=settings.gemini_api_key,
            model=settings.gemini_search_model,
            enabled=settings.google_search_enabled,
            live_enabled=settings.ai_live_calls_enabled,
            timeout=settings.search_timeout_seconds,
            max_retries=settings.ai_max_retries,
            max_input_chars=min(settings.ai_max_input_chars, 4000),
        )
    raise ProviderUnavailable("unknown_engine", f"Unknown engine '{name}'.")


def resolve(name: str):
    """Return a configured engine or fail loudly. There is no silent fallback."""
    engine = get_engine(name)
    state = engine.availability()
    if not state["available"]:
        raise ProviderUnavailable(
            f"{name}_{state['reason'] or 'unavailable'}",
            f"{state['label']} is not available ({state['reason'] or 'not configured'}).",
        )
    return engine


def availability() -> list[dict[str, Any]]:
    result = []
    for name in ("openai", "gemini", "google_search"):
        state = get_engine(name).availability()
        engine_available = state["available"]
        state.update(health.snapshot(name))
        state["available"] = engine_available and state["cooldown_seconds"] == 0
        if state["cooldown_seconds"]:
            state["reason"] = "cooling_down"
        state["state"], state["detail"] = _describe(state, engine_available)
        result.append(state)
    return result


def _describe(state: dict[str, Any], engine_available: bool) -> tuple[str, str]:
    if state["cooldown_seconds"]:
        seconds = state["cooldown_seconds"]
        if state.get("last_error_category") == "quota_exhausted":
            return (
                "quota_exhausted",
                f"Quota or credit balance reported exhausted. Retrying in {seconds}s.",
            )
        return ("temporarily_unavailable", f"Temporarily unavailable. Retrying in {seconds}s.")
    if not engine_available and state.get("reason"):
        return REASON_STATE.get(
            state["reason"], ("unavailable", "This provider cannot be called right now.")
        )
    if state.get("last_success"):
        return ("available", f"Last successful call {state['last_success']}.")
    # Complete configuration with no successful call yet: selectable, but unproven.
    return ("configured", "Configuration looks complete; no successful call has been recorded yet.")


def config_summary() -> dict[str, Any]:
    defaults = job_engines(None)
    return {
        **defaults,
        "live_calls_enabled": settings.ai_live_calls_enabled,
        "research_provider": settings.research_provider,
        "google_search_enabled": settings.google_search_enabled,
        "max_input_chars": settings.ai_max_input_chars,
        "max_output_tokens": settings.ai_max_output_tokens,
        "max_retries": settings.ai_max_retries,
        "auto_fallback_enabled": settings.ai_auto_fallback_enabled,
        "provider_order": provider_order(),
        "fallback_max_attempts": settings.ai_fallback_max_attempts,
        "provider_cooldown_seconds": settings.ai_provider_cooldown_seconds,
    }


def job_engines(selection: Optional[dict[str, Any]]) -> dict[str, str]:
    """Merge a per-job selection over server defaults, validating identifiers."""
    chosen = selection or {}
    merged = {
        "claim_extraction": _pick(chosen, "claim_extraction", settings.claim_engine)
        or "deterministic",
        "research": _pick(chosen, "research", settings.research_engine)
        or settings.research_provider
        or "wikipedia",
        "analysis": _pick(chosen, "analysis", settings.analysis_engine),
        "review": _pick(chosen, "review", settings.review_engine),
        "second_review": _pick(chosen, "second_review", settings.second_review_engine),
    }
    _require(merged["claim_extraction"], ALLOWED_CLAIM, "claim extraction")
    _require(merged["research"], ALLOWED_RESEARCH, "research")
    _require(merged["analysis"], ALLOWED_ANALYSIS, "analysis")
    _require(merged["review"], ALLOWED_REVIEW, "review")
    _require(merged["second_review"], ALLOWED_REVIEW, "second review")
    return merged


def test_engine(name: str) -> dict[str, Any]:
    engine = resolve(name)
    result = engine.test()
    return {"engine": name, "availability": engine.availability(), **result}


def _pick(selection: dict[str, Any], key: str, default: str) -> str:
    value = selection.get(key)
    if value is None:
        return default or ""
    return str(value).strip().lower()


def _require(value: str, allowed: set[str], label: str) -> None:
    if value not in allowed:
        raise ProviderUnavailable(
            "invalid_engine_selection",
            f"Unsupported {label} engine '{value}'.",
        )
