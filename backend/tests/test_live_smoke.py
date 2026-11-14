"""Opt-in live provider smoke tests.

These spend real API credits. They only run when the operator explicitly sets
PROOFLOOP_LIVE_SMOKE_AUTHORIZED=true together with working keys and
PROOFLOOP_AI_LIVE_CALLS_ENABLED=true. Without all of that they skip.

Run with:  pytest tests/test_live_smoke.py -m live -v
"""

from __future__ import annotations

import os

import pytest

from app import config

pytestmark = pytest.mark.live


def _authorised(engine: str) -> None:
    if os.getenv("PROOFLOOP_LIVE_SMOKE_AUTHORIZED", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        pytest.skip("Set PROOFLOOP_LIVE_SMOKE_AUTHORIZED=true to authorise live calls.")
    if not config.settings.ai_live_calls_enabled:
        pytest.skip("Set PROOFLOOP_AI_LIVE_CALLS_ENABLED=true to authorise live calls.")
    from app.engines import registry

    state = registry.get_engine(engine).availability()
    if not state["available"]:
        pytest.skip(f"{engine} unavailable: {state['reason']}")


def test_live_openai_structured_response():
    _authorised("openai")
    from app.engines import registry

    call = registry.resolve("openai").test()
    assert call["ok"] is True
    assert call["usage"]["provider"] == "openai"


def test_live_gemini_structured_response():
    _authorised("gemini")
    from app.engines import registry

    call = registry.resolve("gemini").test()
    assert call["ok"] is True
    assert call["usage"]["provider"] == "gemini"


def test_live_google_search_grounding():
    _authorised("google_search")
    from app.engines import registry

    result = registry.test_engine("google_search")
    assert result["ok"] is True
    # Grounding may legitimately return zero citations for some queries; the
    # call itself must succeed and report its query provenance.
    assert "queries" in result["detail"] or "citation" in result["detail"]
