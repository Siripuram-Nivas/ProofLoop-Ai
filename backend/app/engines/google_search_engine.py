from __future__ import annotations

import logging
import time
from typing import Any, Callable, Optional
from urllib.parse import urlsplit, urlunsplit

from .base import (
    availability,
    call_with_retries,
    clamp,
    new_correlation_id,
    sdk_available,
    utcnow,
)
from .errors import (
    EngineError,
    ProviderRateLimit,
    ProviderTimeout,
    ProviderUnavailable,
)
from .gemini_engine import _map_gemini_error, _raise_for_block
from .schemas import SearchDiscovery, SearchSource

logger = logging.getLogger("proofloop.engines.google_search")

SEARCH_PROMPT = """Research the claim below using Google Search. Look for primary or reputable
sources that report the specific facts in the claim. Do not decide whether the claim is true;
describe what the sources say. Do not invent citations.

CLAIM:
{claim}
"""

ExcerptResolver = Callable[[str, str], dict]


def _default_resolver(url: str, claim_text: str) -> dict:
    # Imported lazily: research imports extraction, which imports this package.
    from ..services.research import excerpt_from_url

    return excerpt_from_url(url, claim_text)


class GoogleSearchEngine:
    engine_id = "google_search"
    label = "Google Search (Gemini grounding)"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        enabled: bool,
        live_enabled: bool,
        timeout: float = 25,
        max_retries: int = 1,
        max_input_chars: int = 4000,
        excerpt_resolver: Optional[ExcerptResolver] = None,
        client: Any = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.enabled = enabled
        self.live_enabled = live_enabled
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_input_chars = max_input_chars
        self._resolver = excerpt_resolver or _default_resolver
        self._client = client

    def availability(self) -> dict[str, Any]:
        configured = bool(self.enabled and self.api_key and self.model)
        sdk = sdk_available("google.genai")
        available = configured and sdk and self.live_enabled
        if not self.enabled:
            reason = "search_disabled"
        elif not sdk:
            reason = "sdk_missing"
        elif not self.api_key:
            reason = "missing_api_key"
        elif not self.model:
            reason = "missing_model"
        elif not self.live_enabled:
            reason = "live_calls_disabled"
        else:
            reason = None
        return availability(
            engine_id=self.engine_id,
            label=self.label,
            configured=configured,
            available=available,
            model=self.model or None,
            live_enabled=self.live_enabled,
            capabilities=["source_discovery", "citation_grounding"],
            reason=reason,
        )

    def _require(self) -> None:
        if not self.enabled:
            raise ProviderUnavailable(
                "search_disabled",
                "Google Search grounding is disabled. Set GOOGLE_SEARCH_ENABLED=true to opt in.",
            )
        if not self.live_enabled:
            raise ProviderUnavailable(
                "live_calls_disabled",
                "Live AI calls are disabled. Set PROOFLOOP_AI_LIVE_CALLS_ENABLED=true to opt in.",
            )
        if not self.api_key:
            raise ProviderUnavailable("missing_api_key", "GEMINI_API_KEY is not configured.")
        if not self.model:
            raise ProviderUnavailable("missing_model", "GEMINI_SEARCH_MODEL is not configured.")
        if not sdk_available("google.genai"):
            raise ProviderUnavailable("sdk_missing", "The google-genai SDK is not installed.")

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        self._require()
        from google import genai
        from google.genai import types

        options = types.HttpOptions(timeout=max(1, int(self.timeout * 1000)))
        self._client = genai.Client(api_key=self.api_key, http_options=options)
        return self._client

    def search(self, claim_text: str) -> SearchDiscovery:
        self._require()
        client = self._client_or_create()
        from google.genai import types

        correlation_id = new_correlation_id()
        started = time.monotonic()
        config = types.GenerateContentConfig(
            temperature=0.0,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )
        prompt = clamp(SEARCH_PROMPT.format(claim=claim_text), self.max_input_chars)

        def run() -> Any:
            try:
                return client.models.generate_content(
                    model=self.model, contents=prompt, config=config
                )
            except Exception as exc:
                raise _map_gemini_error(exc) from exc

        response = call_with_retries(run, retries=self.max_retries)
        _raise_for_block(response)

        metadata = None
        for candidate in _get(response, "candidates", []) or []:
            metadata = _get(candidate, "grounding_metadata", None) or metadata
        queries = [str(q) for q in (_get(metadata, "web_search_queries", []) or [])]
        chunks = _get(metadata, "grounding_chunks", []) or []
        supports = _get(metadata, "grounding_supports", []) or []
        entry_point = _get(metadata, "search_entry_point", None)

        sources: list[SearchSource] = []
        seen: set[str] = set()
        invalid = 0
        retrieved_at = utcnow()
        for index, chunk in enumerate(chunks):
            web = _get(chunk, "web", None)
            if not web:
                continue
            raw_url = _get(web, "uri", None)
            normalised = _normalise_url(raw_url)
            if normalised is None:
                invalid += 1
                continue
            if normalised in seen:
                continue
            seen.add(normalised)
            title = _get(web, "title", None)
            publisher = _get(web, "domain", None) or urlsplit(normalised).hostname
            retrieved = None
            note = None
            accessible = False
            locator = f"grounding_chunk:{index}"
            try:
                retrieved = self._resolver(normalised, claim_text)
                accessible = bool(retrieved.get("accessible"))
                locator = retrieved.get("locator") or locator
                note = retrieved.get("note")
            except Exception as exc:  # retrieval must never break discovery
                note = f"Source retrieval failed ({exc.__class__.__name__})."
            sources.append(
                SearchSource(
                    url=normalised,
                    title=str(title) if title else None,
                    publisher=str(publisher) if publisher else None,
                    retrieved_at=retrieved_at,
                    excerpt=retrieved.get("excerpt") if retrieved else None,
                    locator=locator,
                    accessible=accessible,
                    note=note,
                    provenance={
                        "discovery": "gemini_google_search_grounding",
                        "chunk_index": index,
                        "queries": queries,
                    },
                )
            )

        usage_meta = _get(response, "usage_metadata", None)
        usage = {
            "provider": self.engine_id,
            "model": self.model,
            "request_id": _get(response, "response_id", None),
            "correlation_id": correlation_id,
            "input_tokens": _get(usage_meta, "prompt_token_count", None),
            "output_tokens": _get(usage_meta, "candidates_token_count", None),
            "total_tokens": _get(usage_meta, "total_token_count", None),
            "latency_ms": int((time.monotonic() - started) * 1000),
            "at": utcnow(),
        }
        return SearchDiscovery(
            queries=queries,
            sources=sources,
            invalid_sources=invalid,
            grounding={
                "web_search_queries": queries,
                "chunk_count": len(chunks),
                "support_count": len(supports),
                "has_search_entry_point": entry_point is not None,
                "rendered_content": clamp(
                    str(_get(entry_point, "rendered_content", "") or ""), 4000
                ),
            },
            usage=usage,
        )

    def test(self) -> dict[str, Any]:
        result = self.search("The Eiffel Tower is 330 metres tall.")
        return {
            "ok": True,
            "detail": (
                f"{len(result.queries)} search query(ies), {len(result.sources)} unique citation(s), "
                f"{sum(1 for s in result.sources if s.accessible)} source(s) retrieved."
            ),
            "usage": result.usage,
        }


def _get(obj: Any, key: str, default: Any = None) -> Any:
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _normalise_url(url: Any) -> Optional[str]:
    if not isinstance(url, str):
        return None
    value = url.strip()
    if not value or len(value) > 2000:
        return None
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return None
    if parts.username or parts.password:
        return None
    netloc = parts.hostname.lower()
    if parts.port and parts.port not in {80, 443}:
        netloc = f"{netloc}:{parts.port}"
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), netloc, path, parts.query, ""))
