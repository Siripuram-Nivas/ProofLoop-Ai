"""One-shot, opt-in live provider smoke test.

Sends exactly one request per provider with retries disabled. It never creates a
verification job, never touches SQLite, and never writes to Momen.

Usage (from backend/):
    $env:PROOFLOOP_LIVE_SMOKE_AUTHORIZED = "true"
    .\.venv\Scripts\python.exe scripts\live_smoke.py

PROOFLOOP_AI_LIVE_CALLS_ENABLED in .env is not consulted or changed: the live
gate is enabled in-process only for this run.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.engines.errors import EngineError  # noqa: E402
from app.engines.gemini_engine import GeminiEngine  # noqa: E402
from app.engines.google_search_engine import GoogleSearchEngine  # noqa: E402
from app.engines.openai_engine import OpenAIEngine  # noqa: E402

CLAIM = "The Eiffel Tower is 330 metres tall."
TEXT = "The Eiffel Tower is 330 metres tall and was completed in 1889."


def _common() -> dict:
    return {
        "live_enabled": True,
        "timeout": settings.ai_timeout_seconds,
        "max_retries": 0,
        "max_input_chars": settings.ai_max_input_chars,
        "max_output_tokens": settings.ai_max_output_tokens,
    }


def run_openai() -> dict:
    engine = OpenAIEngine(
        api_key=settings.openai_api_key, model=settings.openai_model, **_common()
    )
    try:
        call = engine.extract_claims(TEXT)
    except EngineError as exc:
        return {"ok": False, "code": exc.code, "message": exc.message}
    return {
        "ok": True,
        "model": engine.model,
        "request_id": call.usage.get("request_id"),
        "usage": call.usage,
        "validated": True,
        "claims": [claim.text for claim in call.data.claims],
    }


def run_gemini() -> dict:
    engine = GeminiEngine(
        api_key=settings.gemini_api_key, model=settings.gemini_model, **_common()
    )
    try:
        # No evidence supplied on purpose: nothing is fabricated for a review.
        call = engine.review_claim(CLAIM, [], [])
    except EngineError as exc:
        return {"ok": False, "code": exc.code, "message": exc.message}
    review = call.data
    return {
        "ok": True,
        "model": engine.model,
        "request_id": call.usage.get("request_id"),
        "usage": call.usage,
        "validated": True,
        "recommended_verdict": review.recommended_verdict,
        "confidence": review.confidence,
        "concerns": review.concerns,
        "reasoning_chars": len(review.reasoning),
    }


def run_search() -> dict:
    engine = GoogleSearchEngine(
        api_key=settings.gemini_api_key,
        model=settings.gemini_search_model,
        enabled=settings.google_search_enabled,
        live_enabled=True,
        timeout=settings.search_timeout_seconds,
        max_retries=0,
        max_input_chars=min(settings.ai_max_input_chars, 4000),
    )
    try:
        result = engine.search(CLAIM)
    except EngineError as exc:
        return {"ok": False, "code": exc.code, "message": exc.message}
    return {
        "ok": True,
        "model": engine.model,
        "usage": result.usage,
        "queries": result.queries,
        "citation_count": len(result.sources),
        "invalid_sources": result.invalid_sources,
        "grounding": {k: v for k, v in result.grounding.items() if k != "rendered_content"},
        "has_rendered_entry_point": bool(result.grounding.get("rendered_content")),
        "citations": [
            {
                "url": source.url,
                "title": source.title,
                "publisher": source.publisher,
                "accessible": source.accessible,
                "excerpt_chars": len(source.excerpt or ""),
                "locator": source.locator,
                "note": source.note,
            }
            for source in result.sources
        ],
    }


def main() -> int:
    if os.getenv("PROOFLOOP_LIVE_SMOKE_AUTHORIZED", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        print("Not authorised. Set PROOFLOOP_LIVE_SMOKE_AUTHORIZED=true to spend real credits.")
        return 2

    report = {
        "openai": run_openai(),
        "gemini": run_gemini(),
        "google_search": run_search(),
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if all(item.get("ok") for item in report.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
