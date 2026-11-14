from __future__ import annotations

import importlib.util
import logging
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional, TypeVar

from .errors import EngineError

logger = logging.getLogger("proofloop.engines")

T = TypeVar("T")

MAX_RETRY_DELAY = 10.0


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clamp(text: str, limit: int) -> str:
    text = text or ""
    return text if len(text) <= limit else text[:limit]


def sdk_available(module: str) -> bool:
    try:
        return importlib.util.find_spec(module) is not None
    except (ImportError, ValueError):
        return False


@dataclass
class EngineCall:
    data: Any
    usage: dict[str, Any] = field(default_factory=dict)


def usage_payload(
    *,
    provider: str,
    model: str,
    request_id: Optional[str],
    correlation_id: str,
    started: float,
    input_tokens: Optional[int] = None,
    output_tokens: Optional[int] = None,
    total_tokens: Optional[int] = None,
) -> dict[str, Any]:
    return {
        "provider": provider,
        "model": model,
        "request_id": request_id,
        "correlation_id": correlation_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "latency_ms": int((time.monotonic() - started) * 1000),
        "at": utcnow(),
    }


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def call_with_retries(
    fn: Callable[[], T],
    *,
    retries: int,
    base_delay: float = 0.5,
) -> T:
    """Retry only provider-signalled retryable failures, with bounded backoff."""
    attempt = 0
    while True:
        try:
            return fn()
        except EngineError as exc:
            if not exc.retryable or attempt >= max(0, retries):
                raise
            # Retry-After is honoured but capped: waiting longer than this is worse
            # than letting the router switch providers.
            delay = exc.retry_after if exc.retry_after is not None else base_delay * (2**attempt)
            delay = min(delay, MAX_RETRY_DELAY)
            delay += random.uniform(0, delay * 0.2)
            logger.warning(
                "engine retry %s/%s after %s: %s",
                attempt + 1,
                retries,
                exc.code,
                exc.message,
            )
            time.sleep(delay)
            attempt += 1


def availability(
    *,
    engine_id: str,
    label: str,
    configured: bool,
    available: bool,
    model: Optional[str],
    live_enabled: bool,
    capabilities: list[str],
    reason: Optional[str] = None,
) -> dict[str, Any]:
    return {
        "id": engine_id,
        "label": label,
        "configured": configured,
        "available": available,
        "live_enabled": live_enabled,
        "model": model,
        "capabilities": capabilities,
        "reason": reason,
    }
