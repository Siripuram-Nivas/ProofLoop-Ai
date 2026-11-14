from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.config import settings
from app.engines import health, registry, router
from app.engines.base import EngineCall
from app.engines.classify import classify_gemini, classify_openai
from app.engines.errors import (
    AllProvidersFailed,
    EngineError,
    ProviderOutputError,
    ProviderRateLimit,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.engines.schemas import ClaimReview


@pytest.fixture(autouse=True)
def clear_health():
    health.reset()
    yield
    health.reset()


def review(verdict: str = "supported") -> ClaimReview:
    return ClaimReview(
        claim_text="The tower is 330 metres tall.",
        recommended_verdict=verdict,
        confidence=0.5,
        concerns=["one source"],
        reasoning="Reasoning from the supplied evidence.",
    )


def quota_error() -> EngineError:
    return EngineError(
        "provider_quota_exhausted",
        "Provider reports no remaining credits.",
        status=402,
        category="quota_exhausted",
    )


def auth_error() -> EngineError:
    return EngineError(
        "provider_auth_failed", "Provider rejected the credentials.", category="auth"
    )


class Fake:
    def __init__(self, result: ClaimReview | None = None, error: EngineError | None = None):
        self.result = result or review()
        self.error = error
        self.calls = 0

    def review_claim(self, *_args, **_kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return EngineCall(
            data=self.result,
            usage={"provider": "fake", "total_tokens": 5, "request_id": "req_1"},
        )


def wire(monkeypatch, engines: dict, configured=("openai", "gemini"), **overrides):
    monkeypatch.setattr(registry, "get_engine", lambda name: engines[name])
    monkeypatch.setattr(registry, "is_configured", lambda name: name in configured)
    patched = replace(
        settings,
        ai_auto_fallback_enabled=overrides.pop("auto_fallback", True),
        ai_provider_order=overrides.pop("order", ("openai", "gemini")),
        ai_fallback_max_attempts=overrides.pop("max_attempts", 2),
        ai_provider_cooldown_seconds=overrides.pop("cooldown", 300.0),
        **overrides,
    )
    # registry owns the priority list, router owns the attempt/cooldown knobs.
    monkeypatch.setattr(registry, "settings", patched)
    monkeypatch.setattr(router, "settings", patched)


# 1 ---------------------------------------------------------------------------
def test_primary_success_does_not_call_fallback(monkeypatch):
    engines = {"openai": Fake(), "gemini": Fake()}
    wire(monkeypatch, engines)
    routed = router.call("review", "review_claim", "openai", "claim", [], [])
    assert routed.engine == "openai"
    assert routed.used_fallback is False
    assert engines["openai"].calls == 1
    assert engines["gemini"].calls == 0


# 2 ---------------------------------------------------------------------------
def test_openai_quota_exhausted_switches_to_gemini(monkeypatch):
    engines = {"openai": Fake(error=quota_error()), "gemini": Fake()}
    wire(monkeypatch, engines)
    routed = router.call("review", "review_claim", "openai", "claim", [], [])
    assert routed.engine == "gemini"
    assert routed.used_fallback is True
    assert routed.attempts[0]["outcome"] == "quota_exhausted"
    assert routed.call.data.recommended_verdict == "supported"


# 3 ---------------------------------------------------------------------------
def test_gemini_quota_exhausted_switches_to_openai(monkeypatch):
    engines = {"openai": Fake(), "gemini": Fake(error=quota_error())}
    wire(monkeypatch, engines)
    routed = router.call("review", "review_claim", "gemini", "claim", [], [])
    assert routed.engine == "openai"
    assert engines["gemini"].calls == 1
    assert engines["openai"].calls == 1


# 4 ---------------------------------------------------------------------------
def test_both_providers_exhausted_returns_clean_error(monkeypatch):
    engines = {"openai": Fake(error=quota_error()), "gemini": Fake(error=quota_error())}
    wire(monkeypatch, engines)
    with pytest.raises(AllProvidersFailed) as exc:
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert exc.value.code == "all_providers_failed"
    assert [item["outcome"] for item in exc.value.attempts] == [
        "quota_exhausted",
        "quota_exhausted",
    ]
    assert "no remaining credits" in exc.value.message
    assert engines["openai"].calls == 1 and engines["gemini"].calls == 1


# 5 ---------------------------------------------------------------------------
def test_openai_rate_limit_falls_back_without_repeating(monkeypatch):
    engines = {"openai": Fake(error=ProviderRateLimit()), "gemini": Fake()}
    wire(monkeypatch, engines)
    routed = router.call("review", "review_claim", "openai", "claim", [], [])
    assert routed.engine == "gemini"
    assert engines["openai"].calls == 1
    assert len(routed.attempts) == 2


# 6 ---------------------------------------------------------------------------
class GeminiQuota(Exception):
    status_code = 429


def test_gemini_quota_classification():
    exc = GeminiQuota(
        "429 RESOURCE_EXHAUSTED. You exceeded your current quota, please check your plan"
    )
    error = classify_gemini(exc)
    assert error.category == "quota_exhausted"
    assert error.code == "provider_quota_exhausted"
    assert error.retryable is False


def test_gemini_payment_required_and_plain_rate_limit():
    payment = GeminiQuota("prepaid credit balance is depleted")
    payment.status_code = 402
    assert classify_gemini(payment).category == "quota_exhausted"
    plain = GeminiQuota("429 rate_limit_exceeded, retry shortly")
    assert classify_gemini(plain).category == "rate_limited"


def test_openai_quota_codes_are_classified_from_body():
    class RateLimitError(Exception):
        status_code = 429
        body = {"code": "organization_spend_limit_exceeded"}

    assert classify_openai(RateLimitError("slow down")).category == "quota_exhausted"

    class PlainRateLimit(Exception):
        status_code = 429
        body = {"code": "rate_limit_exceeded"}

    assert classify_openai(PlainRateLimit("slow down")).category == "rate_limited"


# 7 ---------------------------------------------------------------------------
def test_invalid_api_key_does_not_fall_back(monkeypatch):
    engines = {"openai": Fake(error=auth_error()), "gemini": Fake()}
    wire(monkeypatch, engines)
    with pytest.raises(EngineError) as exc:
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert exc.value.code == "provider_auth_failed"
    assert engines["gemini"].calls == 0


# 8 ---------------------------------------------------------------------------
def test_invalid_request_does_not_fall_back(monkeypatch):
    invalid = EngineError(
        "provider_invalid_request", "Bad request.", category="invalid_request"
    )
    engines = {"openai": Fake(error=invalid), "gemini": Fake()}
    wire(monkeypatch, engines)
    with pytest.raises(EngineError) as exc:
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert exc.value.code == "provider_invalid_request"
    assert engines["gemini"].calls == 0


# 9 ---------------------------------------------------------------------------
def test_both_providers_unconfigured(monkeypatch):
    wire(monkeypatch, {}, configured=())
    with pytest.raises(ProviderUnavailable) as exc:
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert exc.value.code == "no_providers_configured"


# 10 --------------------------------------------------------------------------
def test_fallback_disabled_uses_primary_only(monkeypatch):
    engines = {"openai": Fake(error=quota_error()), "gemini": Fake()}
    wire(monkeypatch, engines, auto_fallback=False)
    with pytest.raises(EngineError) as exc:
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert exc.value.code == "provider_quota_exhausted"
    assert engines["gemini"].calls == 0


# 11 --------------------------------------------------------------------------
def test_quota_cooldown_skips_exhausted_provider(monkeypatch):
    engines = {"openai": Fake(error=quota_error()), "gemini": Fake()}
    wire(monkeypatch, engines)
    first = router.call("review", "review_claim", "openai", "claim", [], [])
    second = router.call("review", "review_claim", "openai", "claim", [], [])
    assert first.engine == second.engine == "gemini"
    assert engines["openai"].calls == 1
    assert health.cooldown_remaining("openai") > 0


# 12 --------------------------------------------------------------------------
def test_provider_recovers_after_cooldown(monkeypatch):
    engines = {"openai": Fake(error=quota_error()), "gemini": Fake()}
    wire(monkeypatch, engines, cooldown=0.0)
    router.call("review", "review_claim", "openai", "claim", [], [])
    router.call("review", "review_claim", "openai", "claim", [], [])
    assert engines["openai"].calls == 2


# 13 --------------------------------------------------------------------------
def test_fallback_output_uses_the_same_validated_model(monkeypatch):
    engines = {"openai": Fake(error=quota_error()), "gemini": Fake(result=review("mixed"))}
    wire(monkeypatch, engines)
    routed = router.call("review", "review_claim", "openai", "claim", [], [])
    assert isinstance(routed.call.data, ClaimReview)
    assert routed.call.data.recommended_verdict == "mixed"


def test_invalid_output_is_not_papered_over_by_fallback(monkeypatch):
    engines = {
        "openai": Fake(error=ProviderOutputError("Gemini returned invalid output.")),
        "gemini": Fake(),
    }
    wire(monkeypatch, engines)
    with pytest.raises(EngineError) as exc:
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert exc.value.code == "provider_invalid_output"
    assert engines["gemini"].calls == 0


# 14 --------------------------------------------------------------------------
def test_no_api_key_in_status_or_errors(monkeypatch):
    monkeypatch.setattr(
        registry,
        "settings",
        replace(
            settings,
            openai_api_key="sk-secret-openai-value",
            openai_model="m",
            gemini_api_key="secret-gemini-value",
        ),
    )
    payload = json.dumps(registry.availability()) + json.dumps(registry.config_summary())
    assert "sk-secret-openai-value" not in payload
    assert "secret-gemini-value" not in payload

    engines = {"openai": Fake(error=quota_error()), "gemini": Fake(error=quota_error())}
    wire(monkeypatch, engines)
    with pytest.raises(AllProvidersFailed) as exc:
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert "sk-secret-openai-value" not in str(exc.value)


# 15 --------------------------------------------------------------------------
def test_attempts_are_bounded_by_configuration(monkeypatch):
    engines = {"openai": Fake(error=quota_error()), "gemini": Fake()}
    wire(monkeypatch, engines, max_attempts=1)
    with pytest.raises(EngineError):
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert engines["openai"].calls == 1
    assert engines["gemini"].calls == 0


# 16 --------------------------------------------------------------------------
def test_grounding_is_never_routed_to_openai(monkeypatch):
    engines = {
        "google_search": Fake(error=quota_error()),
        "openai": Fake(),
        "gemini": Fake(error=quota_error()),
    }
    wire(monkeypatch, engines, configured=("openai", "gemini", "google_search"))
    assert router.provider_order("google_search") == ["google_search"]
    with pytest.raises(EngineError) as exc:
        router.call("research", "review_claim", "google_search", "claim", [], [])
    assert exc.value.code == "provider_quota_exhausted"
    assert engines["openai"].calls == 0
    assert engines["gemini"].calls == 0


# extra ----------------------------------------------------------------------
def test_timeout_records_unknown_outcome_without_replay(monkeypatch):
    engines = {"openai": Fake(error=ProviderTimeout()), "gemini": Fake()}
    wire(monkeypatch, engines)
    with pytest.raises(EngineError) as exc:
        router.call("review", "review_claim", "openai", "claim", [], [])
    assert exc.value.outcome_unknown is True
    assert engines["gemini"].calls == 0


def test_reverse_priority_order_is_honoured(monkeypatch):
    engines = {"openai": Fake(), "gemini": Fake()}
    wire(monkeypatch, engines, order=("gemini", "openai"))
    routed = router.call("review", "review_claim", None, "claim", [], [])
    assert routed.engine == "gemini"


def test_switch_notice_matches_observed_attempts(monkeypatch):
    engines = {"openai": Fake(error=quota_error()), "gemini": Fake()}
    wire(monkeypatch, engines)
    routed = router.call("review", "review_claim", "openai", "claim", [], [])
    text = router.notice(routed.attempts)
    assert text == "OpenAI quota exhausted. Switched to Gemini."


# readiness states -------------------------------------------------------------
def test_state_disabled_when_live_calls_are_off():
    state = {"reason": "live_calls_disabled", "cooldown_seconds": 0, "last_success": None}
    assert registry._describe(state, False)[0] == "disabled"


def test_state_missing_key_is_reported_as_missing_key():
    state = {"reason": "missing_api_key", "cooldown_seconds": 0, "last_success": None}
    assert registry._describe(state, False)[0] == "missing_api_key"


def test_state_configured_before_first_success():
    state = {"reason": None, "cooldown_seconds": 0, "last_success": None}
    assert registry._describe(state, True)[0] == "configured"


def test_state_available_after_a_recorded_success():
    state = {"reason": None, "cooldown_seconds": 0, "last_success": "2026-01-01T00:00:00Z"}
    assert registry._describe(state, True)[0] == "available"


def test_state_quota_exhausted_during_cooldown():
    state = {
        "reason": "cooling_down",
        "cooldown_seconds": 120,
        "last_error_category": "quota_exhausted",
        "last_success": None,
    }
    label, detail = registry._describe(state, True)
    assert label == "quota_exhausted"
    assert "120s" in detail


def test_state_temporary_after_a_non_quota_cooldown():
    state = {
        "reason": "cooling_down",
        "cooldown_seconds": 60,
        "last_error_category": "auth",
        "last_success": None,
    }
    assert registry._describe(state, True)[0] == "temporarily_unavailable"


def test_availability_reports_states_without_secrets(monkeypatch):
    monkeypatch.setattr(
        registry,
        "settings",
        replace(
            settings,
            openai_api_key="sk-leak-openai",
            openai_model="m",
            gemini_api_key="leak-gemini",
            gemini_model="g",
            gemini_search_model="g",
            google_search_enabled=True,
            ai_live_calls_enabled=True,
        ),
    )
    states = {item["id"]: item for item in registry.availability()}
    assert set(states) == {"openai", "gemini", "google_search"}
    assert states["openai"]["state"] in {"configured", "available"}
    assert states["google_search"]["state"] in {"configured", "available"}
    text = json.dumps(registry.availability())
    assert "sk-leak-openai" not in text
    assert "leak-gemini" not in text
