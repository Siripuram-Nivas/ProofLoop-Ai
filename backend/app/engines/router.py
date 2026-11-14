"""Central provider router.

Attempts the preferred provider, then the next configured provider when the failure is
one that another provider could plausibly fix (quota, throttling, temporary outage).
Never retries a request that failed for a reason the request itself caused, and never
replays a request whose outcome is unknown.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from ..config import settings
from . import health, registry
from .base import EngineCall
from .errors import AllProvidersFailed, EngineError, ProviderUnavailable
from .registry import PROVIDER_IDS

logger = logging.getLogger("proofloop.router")

LABELS = {"openai": "OpenAI", "gemini": "Gemini", "google_search": "Google Search"}
FALLBACK_CATEGORIES = {
    "quota_exhausted",
    "rate_limited",
    "temporary",
    "connection",
    "unavailable",
}
REASON_TEXT = {
    "quota_exhausted": "quota exhausted",
    "rate_limited": "rate limited",
    "temporary": "temporarily unavailable",
    "connection": "unreachable",
    "unavailable": "unavailable",
    "timeout": "timed out",
}


@dataclass
class RoutedCall:
    engine: str
    call: EngineCall
    attempts: list[dict[str, Any]] = field(default_factory=list)

    @property
    def used_fallback(self) -> bool:
        return len(self.attempts) > 1


def provider_order(preferred: Optional[str] = None) -> list[str]:
    # Grounding is a Gemini capability: it is never routed to a text model.
    if preferred == "google_search":
        return ["google_search"]
    base = registry.provider_order()
    if not preferred:
        return base
    if preferred not in PROVIDER_IDS:
        raise ProviderUnavailable(
            "invalid_engine_selection", f"Unsupported provider '{preferred}'."
        )
    return [preferred] + [name for name in base if name != preferred]


def call(
    stage: str,
    method: str,
    preferred: Optional[str] = None,
    *args: Any,
    **kwargs: Any,
) -> RoutedCall:
    order = provider_order(preferred)
    eligible = [name for name in order if registry.is_configured(name)]
    if not eligible:
        raise ProviderUnavailable(
            "no_providers_configured",
            "No AI provider is configured. Set the provider key and model on the server.",
        )
    if not settings.ai_auto_fallback_enabled:
        eligible = eligible[:1]

    ready = [name for name in eligible if health.is_available(name)]
    if not ready:
        raise ProviderUnavailable(
            "providers_cooling_down",
            "All configured AI providers are cooling down after recent failures.",
        )

    attempts: list[dict[str, Any]] = []
    last: Optional[EngineError] = None
    for name in ready[: max(1, settings.ai_fallback_max_attempts)]:
        engine = registry.get_engine(name)
        if attempts:
            health.record_event(stage, name, "switched")
        health.record_event(stage, name, "started")
        try:
            result = getattr(engine, method)(*args, **kwargs)
        except EngineError as exc:
            last = exc
            health.record_failure(
                name, exc, cooldown_seconds=settings.ai_provider_cooldown_seconds
            )
            health.record_event(stage, name, exc.category, exc.code)
            attempts.append(
                {"provider": name, "outcome": exc.category, "code": exc.code}
            )
            if exc.category == "timeout":
                # The provider may already have processed (and billed) the request.
                exc.outcome_unknown = True
                break
            if exc.category not in FALLBACK_CATEGORIES:
                break
            logger.warning(
                "provider %s failed (%s); trying next provider", name, exc.category
            )
            continue
        health.record_success(name)
        health.record_event(stage, name, "succeeded")
        attempts.append({"provider": name, "outcome": "succeeded", "code": None})
        return RoutedCall(engine=name, call=result, attempts=attempts)

    if len(attempts) > 1:
        detail = last.message if last is not None else "unknown error"
        raise AllProvidersFailed(
            f"All configured AI providers failed. Last error: {detail}", attempts
        )
    if last is not None:
        raise last
    raise ProviderUnavailable(
        "no_providers_configured",
        "No AI provider is configured. Set the provider key and model on the server.",
    )


def notice(attempts: list[dict[str, Any]]) -> Optional[str]:
    """User-facing sentence describing a completed switch, or None."""
    failed = [item for item in attempts if item["outcome"] != "succeeded"]
    succeeded = [item for item in attempts if item["outcome"] == "succeeded"]
    if not failed or not succeeded:
        return None
    first = failed[0]
    reason = REASON_TEXT.get(first["outcome"], "unavailable")
    return (
        f"{LABELS.get(first['provider'], first['provider'])} {reason}. "
        f"Switched to {LABELS.get(succeeded[-1]['provider'], succeeded[-1]['provider'])}."
    )
