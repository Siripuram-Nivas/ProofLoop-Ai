from __future__ import annotations

from typing import Optional


class EngineError(Exception):
    """A provider failure with an app-safe code, message and stable category."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        status: int = 502,
        details: Optional[list[str]] = None,
        category: str = "unknown",
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable
        self.status = status
        self.details = details or []
        self.category = category
        self.retry_after = retry_after
        # Set by the router when a timeout leaves the provider's outcome unknown.
        self.outcome_unknown = False


DISABLED_CODES = {
    "live_calls_disabled",
    "search_disabled",
    "missing_api_key",
    "missing_model",
    "sdk_missing",
}


class ProviderUnavailable(EngineError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(
            code,
            message,
            retryable=False,
            status=503,
            category="disabled" if code in DISABLED_CODES else "unavailable",
        )


class ProviderTimeout(EngineError):
    def __init__(self, message: str = "The provider did not respond in time.") -> None:
        super().__init__(
            "provider_timeout", message, retryable=True, status=504, category="timeout"
        )


class ProviderRateLimit(EngineError):
    def __init__(self, message: str = "The provider rate limit was reached.") -> None:
        super().__init__(
            "provider_rate_limited",
            message,
            retryable=True,
            status=429,
            category="rate_limited",
        )


class ProviderRefusal(EngineError):
    def __init__(self, message: str = "The provider refused the request.") -> None:
        super().__init__(
            "provider_refusal", message, retryable=False, status=422, category="refusal"
        )


class ProviderSafetyBlock(EngineError):
    def __init__(self, message: str = "The provider blocked the response for safety reasons.") -> None:
        super().__init__(
            "provider_safety_block",
            message,
            retryable=False,
            status=422,
            category="safety",
        )


class ProviderOutputError(EngineError):
    def __init__(self, message: str) -> None:
        super().__init__(
            "provider_invalid_output",
            message,
            retryable=False,
            status=502,
            category="invalid_output",
        )


class AllProvidersFailed(EngineError):
    """Every eligible provider was tried and refused, failed or was exhausted."""

    def __init__(self, message: str, attempts: list[dict]) -> None:
        super().__init__(
            "all_providers_failed", message, retryable=False, status=503, category="exhausted"
        )
        self.attempts = attempts
