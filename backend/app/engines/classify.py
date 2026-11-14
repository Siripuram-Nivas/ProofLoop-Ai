"""Central provider error classification.

Both SDKs surface failures differently, so the mapping lives here instead of in each
engine. Codes and categories are stable: the router makes fallback decisions from the
category, never from the exception class name.
"""

from __future__ import annotations

from typing import Any, Optional

from .errors import (
    EngineError,
    ProviderRateLimit,
    ProviderTimeout,
)

OPENAI_QUOTA_CODES = {
    "credit_balance_exhausted",
    "insufficient_quota",
    "project_spend_limit_exceeded",
    "organization_spend_limit_exceeded",
    "organization_usage_limit_exceeded",
    "usage_limit_exceeded",
    "billing_hard_limit_reached",
}

GEMINI_QUOTA_MARKERS = (
    "quota",
    "billing",
    "prepaid",
    "depleted",
    "credit balance",
)


def _status(exc: Exception) -> Optional[int]:
    raw = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def _body(exc: Exception) -> dict[str, Any]:
    body = getattr(exc, "body", None)
    return body if isinstance(body, dict) else {}


def _error_code(exc: Exception) -> str:
    code = getattr(exc, "code", None) or _body(exc).get("code")
    return str(code).lower() if code else ""


def _retry_after(exc: Exception) -> Optional[float]:
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    try:
        value = headers.get("retry-after")
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _quota(message: str, detail: str) -> EngineError:
    return EngineError(
        "provider_quota_exhausted",
        message,
        retryable=False,
        status=402,
        category="quota_exhausted",
        details=[detail],
    )


def classify_openai(exc: Exception) -> EngineError:
    name = exc.__class__.__name__
    status = _status(exc)
    code = _error_code(exc)
    message = str(getattr(exc, "message", "") or exc)

    if name in {"APITimeoutError", "TimeoutError", "TimeoutException"}:
        return ProviderTimeout()
    if name == "APIConnectionError" or "connection" in name.lower():
        return EngineError(
            "provider_connection_failed",
            "OpenAI could not be reached.",
            retryable=True,
            status=503,
            category="connection",
        )
    if status == 429 or name == "RateLimitError":
        if code in OPENAI_QUOTA_CODES:
            return _quota("OpenAI reports no remaining credits or spend allowance.", code)
        return ProviderRateLimit()
    if status == 402:
        return _quota("OpenAI reports the account balance is depleted.", code or "402")
    if status == 401 or "authentication" in message.lower():
        return EngineError(
            "provider_auth_failed",
            "OpenAI rejected the credentials.",
            retryable=False,
            status=502,
            category="auth",
        )
    if status == 403:
        return EngineError(
            "provider_permission_denied",
            "OpenAI denied permission for this request.",
            retryable=False,
            status=502,
            category="permission",
        )
    if status == 404 or code == "model_not_found":
        return EngineError(
            "provider_model_not_found",
            "OpenAI does not recognise the configured model.",
            retryable=False,
            status=502,
            category="invalid_model",
        )
    if status is not None and status >= 500:
        return EngineError(
            "provider_unavailable",
            "OpenAI is temporarily unavailable.",
            retryable=True,
            status=502,
            category="temporary",
        )
    if status == 400:
        return EngineError(
            "provider_invalid_request",
            message or "OpenAI rejected the request as invalid.",
            retryable=False,
            status=502,
            category="invalid_request",
        )
    return EngineError(
        "provider_error", "OpenAI request failed.", retryable=False, status=502
    )


def classify_gemini(exc: Exception) -> EngineError:
    name = exc.__class__.__name__
    status = _status(exc)
    text = str(exc)
    lowered = text.lower()

    if name in {"DeadlineExceeded", "TimeoutError", "APITimeoutError", "ReadTimeout"}:
        return ProviderTimeout()
    if name in {
        "ConnectError",
        "ConnectionError",
        "ServerDisconnectedError",
        "ReadError",
    } or "connection" in name.lower():
        return EngineError(
            "provider_connection_failed",
            "Gemini could not be reached.",
            retryable=True,
            status=503,
            category="connection",
        )
    if status == 402:
        return _quota("Gemini reports the prepaid credit balance is depleted.", "402")
    if status == 429 or name in {"ResourceExhausted", "RateLimitError"}:
        if any(marker in lowered for marker in GEMINI_QUOTA_MARKERS):
            return _quota(
                "Gemini reports the API quota is exhausted for this key.",
                "429 RESOURCE_EXHAUSTED",
            )
        return ProviderRateLimit()
    if status == 401 or name == "Unauthenticated":
        return EngineError(
            "provider_auth_failed",
            "Gemini rejected the credentials.",
            retryable=False,
            status=502,
            category="auth",
        )
    if status == 403 or name == "PermissionDenied":
        return EngineError(
            "provider_permission_denied",
            "Gemini denied permission for this request.",
            retryable=False,
            status=502,
            category="permission",
        )
    if status == 404 or "not found" in lowered:
        return EngineError(
            "provider_model_not_found",
            "Gemini does not recognise the configured model.",
            retryable=False,
            status=502,
            category="invalid_model",
        )
    if status is not None and status >= 500:
        return EngineError(
            "provider_unavailable",
            "Gemini is temporarily unavailable.",
            retryable=True,
            status=502,
            category="temporary",
        )
    if status == 400 or name in {"InvalidArgument", "ClientError"}:
        return EngineError(
            "provider_invalid_request",
            "Gemini rejected the request as invalid.",
            retryable=False,
            status=502,
            category="invalid_request",
        )
    return EngineError(
        "provider_error", "Gemini request failed.", retryable=False, status=502
    )
