"""In-process provider health: cooldowns, failure counts and sanitized events.

State is deliberately process-local. ProofLoop runs as a single API process, and the
authoritative record of what happened to a job is still the job snapshot.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

from .base import utcnow

# Categories where retrying the same provider soon is pointless.
COOLDOWN_CATEGORIES = {"quota_exhausted", "auth", "permission"}


@dataclass
class ProviderHealth:
    name: str
    available: bool = True
    last_success: Optional[str] = None
    last_quota_failure: Optional[str] = None
    last_error_category: Optional[str] = None
    cooldown_until: float = 0.0
    failure_count: int = 0


_lock = threading.Lock()
_state: dict[str, ProviderHealth] = {}
_events: deque[dict[str, Any]] = deque(maxlen=200)


def reset() -> None:
    with _lock:
        _state.clear()
        _events.clear()


def _entry(name: str) -> ProviderHealth:
    entry = _state.get(name)
    if entry is None:
        entry = ProviderHealth(name=name)
        _state[name] = entry
    return entry


def record_success(name: str) -> None:
    with _lock:
        entry = _entry(name)
        entry.available = True
        entry.last_success = utcnow()
        entry.cooldown_until = 0.0
        entry.failure_count = 0


def record_failure(
    name: str, error: Exception, *, cooldown_seconds: float
) -> None:
    category = getattr(error, "category", "unknown")
    with _lock:
        entry = _entry(name)
        entry.failure_count += 1
        entry.last_error_category = category
        if category == "quota_exhausted":
            entry.last_quota_failure = utcnow()
        if category in COOLDOWN_CATEGORIES:
            entry.cooldown_until = time.monotonic() + max(0.0, cooldown_seconds)
            entry.available = False


def cooldown_remaining(name: str) -> int:
    with _lock:
        entry = _entry(name)
        return max(0, int(round(entry.cooldown_until - time.monotonic())))


def is_available(name: str) -> bool:
    with _lock:
        entry = _entry(name)
        if entry.cooldown_until and time.monotonic() >= entry.cooldown_until:
            entry.cooldown_until = 0.0
            entry.available = True
        return entry.available


def snapshot(name: str) -> dict[str, Any]:
    with _lock:
        entry = _entry(name)
        remaining = max(0, int(round(entry.cooldown_until - time.monotonic())))
        return {
            "available": remaining == 0,
            "cooldown_seconds": remaining,
            "last_success": entry.last_success,
            "last_quota_failure": entry.last_quota_failure,
            "last_error_category": entry.last_error_category,
            "failure_count": entry.failure_count,
        }


def record_event(
    stage: str, provider: str, outcome: str, code: Optional[str] = None
) -> None:
    # Sanitized: stage/provider/outcome/code only, never payloads or credentials.
    event = {"at": utcnow(), "stage": stage, "provider": provider, "outcome": outcome}
    if code:
        event["code"] = code
    with _lock:
        _events.append(event)


def events(limit: int = 50) -> list[dict[str, Any]]:
    with _lock:
        return list(_events)[-limit:]
