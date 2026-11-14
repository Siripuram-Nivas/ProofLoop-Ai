from __future__ import annotations

import json
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.config import settings
from app.engines import base, registry
from app.engines.errors import (
    EngineError,
    ProviderOutputError,
    ProviderRateLimit,
    ProviderRefusal,
    ProviderSafetyBlock,
    ProviderTimeout,
    ProviderUnavailable,
)
from app.engines.gemini_engine import GeminiEngine
from app.engines.google_search_engine import GoogleSearchEngine
from app.engines.openai_engine import OpenAIEngine
from app.engines.schemas import ClaimExtraction, ClaimReview
from app.services import ai_stages
from app.services.report import build_report


class Obj(SimpleNamespace):
    pass


class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls: list[dict] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response


class FakeOpenAIClient:
    def __init__(self, response=None, error=None):
        self.responses = FakeResponses(response, error)


def openai_engine(client, *, retries=0, live=True):
    return OpenAIEngine(
        api_key="test-key",
        model="test-model",
        live_enabled=live,
        max_retries=retries,
        client=client,
    )


def openai_response(payload: dict | str, *, status="completed", output=None):
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return Obj(
        id="resp_1",
        status=status,
        output=output or [],
        output_text=text,
        incomplete_details=None,
        usage=Obj(input_tokens=11, output_tokens=7, total_tokens=18),
    )


def gemini_client(response=None, error=None):
    class Models:
        def __init__(self):
            self.calls = []

        def generate_content(self, **kwargs):
            self.calls.append(kwargs)
            if error:
                raise error
            return response

    return Obj(models=Models())


def gemini_engine(client, *, retries=0, live=True):
    return GeminiEngine(
        api_key="test-key",
        model="test-model",
        live_enabled=live,
        max_retries=retries,
        client=client,
    )


# ---------------------------------------------------------------- OpenAI


def test_openai_structured_success():
    payload = {"claims": [{"text": "The tower is 330 metres tall.", "category": "quantity"}]}
    client = FakeOpenAIClient(openai_response(payload))
    call = openai_engine(client).extract_claims("The tower is 330 metres tall.")
    assert call.data.claims[0].text == "The tower is 330 metres tall."
    assert call.usage["provider"] == "openai"
    assert call.usage["total_tokens"] == 18
    sent = client.responses.calls[0]
    assert sent["text"]["format"]["type"] == "json_schema"
    assert sent["text"]["format"]["schema"]["additionalProperties"] is False
    assert sent["store"] is False
    assert "temperature" not in sent


def test_openai_strict_schema_is_closed_and_fully_required():
    from app.engines.openai_engine import strict_schema
    from app.engines.schemas import ClaimExtraction

    schema = strict_schema(ClaimExtraction)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    nested = schema["$defs"]["ExtractedClaim"]
    assert nested["additionalProperties"] is False
    assert set(nested["required"]) == set(nested["properties"])
    assert "default" not in json.dumps(schema)


def test_openai_refusal_is_reported():
    response = openai_response(
        "", output=[Obj(type="message", content=[Obj(type="refusal", refusal="No.")])]
    )
    with pytest.raises(ProviderRefusal):
        openai_engine(FakeOpenAIClient(response)).extract_claims("Some claim.")


def test_openai_timeout_retries_then_raises(monkeypatch):
    class APITimeoutError(Exception):
        pass

    sleeps = []
    monkeypatch.setattr(base.time, "sleep", lambda value: sleeps.append(value))
    client = FakeOpenAIClient(error=APITimeoutError("timed out"))
    with pytest.raises(ProviderTimeout):
        openai_engine(client, retries=2).extract_claims("Some claim.")
    assert len(sleeps) == 2
    assert 0.5 <= sleeps[0] <= 0.6
    assert 1.0 <= sleeps[1] <= 1.2


def test_retry_after_is_honoured_but_capped(monkeypatch):
    sleeps = []
    monkeypatch.setattr(base.time, "sleep", lambda value: sleeps.append(value))
    calls = []

    def fail():
        calls.append(1)
        if len(calls) == 1:
            error = ProviderRateLimit()
            error.retry_after = 2.0
            raise error
        return "ok"

    assert base.call_with_retries(fail, retries=1) == "ok"
    assert 2.0 <= sleeps[0] <= 2.4

    sleeps.clear()
    huge = ProviderRateLimit()
    huge.retry_after = 3600.0

    def fail_forever():
        raise huge

    with pytest.raises(ProviderRateLimit):
        base.call_with_retries(fail_forever, retries=1)
    assert sleeps[0] <= base.MAX_RETRY_DELAY * 1.2


def test_openai_rate_limit_is_retryable_and_bounded(monkeypatch):
    class RateLimitError(Exception):
        status_code = 429

    monkeypatch.setattr(base.time, "sleep", lambda value: None)
    client = FakeOpenAIClient(error=RateLimitError("slow down"))
    with pytest.raises(ProviderRateLimit):
        openai_engine(client, retries=1).extract_claims("Some claim.")
    assert len(client.responses.calls) == 2


def test_openai_quota_exhausted_is_not_retried(monkeypatch):
    class RateLimitError(Exception):
        status_code = 429
        code = "insufficient_quota"

    sleeps = []
    monkeypatch.setattr(base.time, "sleep", lambda value: sleeps.append(value))
    client = FakeOpenAIClient(error=RateLimitError("no credits"))
    with pytest.raises(EngineError, match="no remaining credits") as exc:
        openai_engine(client, retries=2).extract_claims("Some claim.")
    assert exc.value.code == "provider_quota_exhausted"
    assert exc.value.retryable is False
    assert sleeps == []
    assert len(client.responses.calls) == 1


def test_gemini_quota_exhausted_is_not_retried(monkeypatch):
    class ResourceExhausted(Exception):
        status_code = 429

    sleeps = []
    monkeypatch.setattr(base.time, "sleep", lambda value: sleeps.append(value))
    engine = gemini_engine(gemini_client(error=ResourceExhausted("quota exceeded")), retries=2)
    with pytest.raises(EngineError) as exc:
        engine.extract_claims("Some claim.")
    assert exc.value.code == "provider_quota_exhausted"
    assert sleeps == []


def test_openai_incomplete_response_is_rejected():
    response = openai_response(
        '{"claims": []}', status="incomplete"
    )
    response.incomplete_details = Obj(reason="max_output_tokens")
    with pytest.raises(ProviderOutputError, match="incomplete"):
        openai_engine(FakeOpenAIClient(response)).extract_claims("Some claim.")


def test_openai_missing_credentials_is_unavailable():
    engine = OpenAIEngine(api_key="", model="m", live_enabled=True)
    assert engine.availability()["available"] is False
    assert engine.availability()["reason"] == "missing_api_key"
    with pytest.raises(ProviderUnavailable):
        engine.extract_claims("Some claim.")


def test_openai_drops_unapproved_source_urls():
    payload = {
        "claim_text": "claim text",
        "notes": [
            {
                "source_url": "https://allowed.example/a",
                "stance": "supports",
                "relevance": 0.8,
                "rationale": "matches",
            },
            {
                "source_url": "https://invented.example/b",
                "stance": "supports",
                "relevance": 0.9,
                "rationale": "invented",
            },
        ],
    }
    call = openai_engine(FakeOpenAIClient(openai_response(payload))).analyze_evidence(
        "claim", [], ["https://allowed.example/a"]
    )
    assert [note.source_url for note in call.data.notes] == ["https://allowed.example/a"]


# ---------------------------------------------------------------- Gemini


def test_gemini_structured_success():
    payload = {
        "claim_text": "The tower is 330 metres tall.",
        "recommended_verdict": "supported",
        "confidence": 0.7,
        "concerns": ["single source"],
        "reasoning": "The excerpt reports the same height.",
    }
    client = gemini_client(Obj(text=json.dumps(payload), parsed=None, candidates=[], prompt_feedback=None, usage_metadata=Obj(prompt_token_count=9, candidates_token_count=5, total_token_count=14), response_id="r1"))
    call = gemini_engine(client).review_claim("claim", [], [])
    assert isinstance(call.data, ClaimReview)
    assert call.data.recommended_verdict == "supported"
    assert call.usage["total_tokens"] == 14


def test_gemini_safety_block_is_reported():
    response = Obj(
        text="",
        parsed=None,
        prompt_feedback=None,
        candidates=[Obj(finish_reason=Obj(value="SAFETY"))],
    )
    with pytest.raises(ProviderSafetyBlock):
        gemini_engine(gemini_client(response)).extract_claims("Some claim.")


def test_gemini_timeout_is_reported(monkeypatch):
    class DeadlineExceeded(Exception):
        pass

    monkeypatch.setattr(base.time, "sleep", lambda value: None)
    with pytest.raises(ProviderTimeout):
        gemini_engine(gemini_client(error=DeadlineExceeded()), retries=1).extract_claims(
            "Some claim."
        )


def test_gemini_parsed_object_is_preserved():
    parsed = ClaimExtraction(claims=[{"text": "A real claim.", "category": "general"}])
    response = Obj(text="", parsed=parsed, candidates=[], prompt_feedback=None, usage_metadata=None, response_id="r2")
    call = gemini_engine(gemini_client(response)).extract_claims("A real claim.")
    assert call.data is parsed


# ---------------------------------------------------------------- Google Search


def grounding(chunks, queries=None, supports=None):
    return Obj(
        web_search_queries=queries or ["eiffel tower height"],
        grounding_chunks=[Obj(web=Obj(**chunk)) for chunk in chunks],
        grounding_supports=supports or [Obj(grounding_chunk_indices=[0])],
        search_entry_point=Obj(rendered_content="<div>citations</div>"),
    )


def search_engine(client, resolver):
    return GoogleSearchEngine(
        api_key="test-key",
        model="test-model",
        enabled=True,
        live_enabled=True,
        max_retries=0,
        client=client,
        excerpt_resolver=resolver,
    )


def test_google_search_multiple_citations_and_deduplication():
    metadata = grounding(
        [
            {"uri": "https://example.org/a", "title": "A", "domain": "example.org"},
            {"uri": "https://example.org/a/#section", "title": "A duplicate", "domain": "example.org"},
            {"uri": "https://example.net/b", "title": "B", "domain": "example.net"},
        ]
    )
    response = Obj(text="", parsed=None, prompt_feedback=None, candidates=[Obj(grounding_metadata=metadata, finish_reason=None)], usage_metadata=None, response_id="r3")
    calls = []

    def resolver(url, claim):
        calls.append(url)
        return {"excerpt": f"Exact excerpt for {url}.", "locator": "page text", "accessible": True, "note": None}

    result = search_engine(gemini_client(response), resolver).search("claim")
    assert [source.url for source in result.sources] == [
        "https://example.org/a",
        "https://example.net/b",
    ]
    assert result.queries == ["eiffel tower height"]
    assert calls == ["https://example.org/a", "https://example.net/b"]
    assert result.sources[0].provenance["discovery"] == "gemini_google_search_grounding"


def test_google_search_missing_annotations_returns_empty():
    response = Obj(text="", parsed=None, prompt_feedback=None, candidates=[Obj(grounding_metadata=None, finish_reason=None)], usage_metadata=None, response_id="r4")
    result = search_engine(gemini_client(response), lambda url, claim: {}).search("claim")
    assert result.sources == []
    assert result.queries == []


def test_google_search_invalid_urls_are_counted_not_emitted():
    metadata = grounding(
        [
            {"uri": "javascript:alert(1)", "title": "Bad", "domain": None},
            {"uri": "not a url", "title": "Also bad", "domain": None},
            {"uri": "https://good.example/page", "title": "Good", "domain": "good.example"},
        ]
    )
    response = Obj(text="", parsed=None, prompt_feedback=None, candidates=[Obj(grounding_metadata=metadata, finish_reason=None)], usage_metadata=None, response_id="r5")
    result = search_engine(
        gemini_client(response),
        lambda url, claim: {"excerpt": "ok", "locator": "page", "accessible": True, "note": None},
    ).search("claim")
    assert result.invalid_sources == 2
    assert [source.url for source in result.sources] == ["https://good.example/page"]


def test_google_search_preserves_exact_excerpt_and_unreadable_state():
    metadata = grounding(
        [
            {"uri": "https://a.example/x", "title": "A", "domain": "a.example"},
            {"uri": "https://b.example/y", "title": "B", "domain": "b.example"},
        ]
    )
    response = Obj(text="", parsed=None, prompt_feedback=None, candidates=[Obj(grounding_metadata=metadata, finish_reason=None)], usage_metadata=None, response_id="r6")
    padded = "  The tower measures 330 metres.  "

    def resolver(url, claim):
        if url.endswith("/x"):
            return {"excerpt": padded, "locator": "paragraph 2", "accessible": True, "note": None}
        return {"excerpt": None, "locator": None, "accessible": False, "note": "Timed out."}

    result = search_engine(gemini_client(response), resolver).search("claim")
    assert result.sources[0].excerpt == padded
    assert result.sources[1].accessible is False
    assert result.sources[1].excerpt is None
    assert result.sources[1].note == "Timed out."


# ---------------------------------------------------------------- registry


def test_registry_selection_and_no_silent_fallback(monkeypatch):
    monkeypatch.setattr(
        registry,
        "settings",
        replace(
            settings,
            openai_api_key="k",
            openai_model="m",
            gemini_api_key="",
            google_search_enabled=False,
            ai_live_calls_enabled=True,
        ),
    )
    assert registry.resolve("openai").availability()["available"] is True
    with pytest.raises(ProviderUnavailable):
        registry.resolve("gemini")


def test_live_calls_disabled_by_default(monkeypatch):
    monkeypatch.setattr(
        registry,
        "settings",
        replace(settings, openai_api_key="k", openai_model="m", ai_live_calls_enabled=False),
    )
    state = registry.get_engine("openai").availability()
    assert state["available"] is False
    assert state["reason"] == "live_calls_disabled"
    with pytest.raises(ProviderUnavailable) as exc:
        registry.resolve("openai")
    assert "live_calls_disabled" in exc.value.code


def test_job_engine_selection_overrides_defaults(monkeypatch):
    monkeypatch.setattr(registry, "settings", replace(settings, claim_engine="", review_engine=""))
    merged = registry.job_engines(
        {"claim_extraction": "openai", "research": "google_search", "review": "gemini"}
    )
    assert merged["claim_extraction"] == "openai"
    assert merged["research"] == "google_search"
    assert merged["review"] == "gemini"
    assert merged["analysis"] == ""
    with pytest.raises(ProviderUnavailable):
        registry.job_engines({"claim_extraction": "chatgpt"})


# ---------------------------------------------------------------- pipeline/report


def make_job(**overrides):
    job = {
        "id": "ver_test",
        "title": "Test",
        "input_kind": "text",
        "input_text": "The tower is 330 metres tall.",
        "engine": {"extraction": "deterministic", "research": "wikipedia"},
        "engines": {
            "claim_extraction": "deterministic",
            "research": "wikipedia",
            "analysis": "",
            "review": "gemini",
            "second_review": "openai",
        },
        "claims": [
            {
                "id": "clm_1",
                "text": "The tower is 330 metres tall.",
                "category": "quantity",
                "confidence": 0.6,
                "verdict": "contradicted",
                "verdict_basis": "The excerpt reports 300 metres.",
                "evidence": [
                    {
                        "id": "ev_1",
                        "relationship": "contradicts",
                        "excerpt": "The tower is 300 metres tall.",
                        "explanation": "Numeric mismatch.",
                        "source_title": "Source",
                        "source_url": "https://source.example/page",
                        "retrieved_at": "2026-11-13T10:00:00Z",
                    }
                ],
            }
        ],
        "sources": [],
        "contradictions": [],
    }
    job.update(overrides)
    return job


class FakeReviewEngine:
    def __init__(self, verdict):
        self.verdict = verdict
        self.calls = 0

    def review_claim(self, claim_text, evidence, conflicts):
        self.calls += 1
        return base.EngineCall(
            data=ClaimReview(
                claim_text=claim_text,
                recommended_verdict=self.verdict,
                confidence=0.9,
                concerns=["one source"],
                reasoning="Model reasoning.",
            ),
            usage={"provider": "fake", "total_tokens": 5},
        )


def test_cross_provider_disagreement_never_changes_deterministic_verdict(monkeypatch):
    gemini = FakeReviewEngine("supported")
    openai = FakeReviewEngine("insufficient")
    engines = {"gemini": gemini, "openai": openai}
    monkeypatch.setattr(registry, "get_engine", lambda name: engines[name])
    monkeypatch.setattr(registry, "is_configured", lambda name: name in engines)
    monkeypatch.setattr(registry, "availability", lambda: [])

    job = make_job()
    ai_stages.apply_ai_stages(job)
    claim = job["claims"][0]
    assert claim["verdict"] == "contradicted"
    assert claim["independent_review"]["agrees_with_deterministic"] is False
    assert claim["second_review"]["agrees_with_deterministic"] is False
    assert job["ai"]["review"]["agreements"] == 0
    report = build_report(job)
    assert report["claims"][0]["verdict"] == "contradicted"
    assert report["claims"][0]["confidence_kind"] == "extraction_confidence"
    assert any("not proof" in item for item in report["limitations"])


def test_engine_failure_is_recorded_not_crashing(monkeypatch):
    def fail(name):
        raise ProviderUnavailable("gemini_live_calls_disabled", "disabled")

    monkeypatch.setattr(registry, "get_engine", fail)
    monkeypatch.setattr(registry, "is_configured", lambda name: True)
    monkeypatch.setattr(registry, "availability", lambda: [])
    job = make_job()
    ai_stages.apply_ai_stages(job)
    assert job["claims"][0]["verdict"] == "contradicted"
    assert job["ai"]["review"]["error"]["code"] == "gemini_live_calls_disabled"


# ---------------------------------------------------------------- API


def test_engine_status_endpoint_hides_secrets(client, guest, monkeypatch):
    monkeypatch.setattr(
        registry,
        "settings",
        replace(settings, openai_api_key="super-secret", openai_model="m"),
    )
    response = client.get("/api/v1/engines")
    assert response.status_code == 200
    body = response.json()
    assert {item["id"] for item in body["engines"]} == {"openai", "gemini", "google_search"}
    assert "super-secret" not in response.text
    assert body["config"]["live_calls_enabled"] is False


def test_engine_test_requires_confirmation(client, guest):
    response = client.post("/api/v1/engines/openai/test", json={})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "confirmation_required"


def test_engine_test_with_live_calls_disabled(client, guest, monkeypatch):
    monkeypatch.setattr(
        registry,
        "settings",
        replace(
            settings,
            openai_api_key="k",
            openai_model="m",
            ai_live_calls_enabled=False,
        ),
    )
    response = client.post("/api/v1/engines/openai/test", json={"confirm": True})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "openai_live_calls_disabled"
