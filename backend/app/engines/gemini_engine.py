from __future__ import annotations

import json
import logging
import time
from typing import Any

from .base import (
    EngineCall,
    availability,
    call_with_retries,
    clamp,
    new_correlation_id,
    sdk_available,
    usage_payload,
)
from .classify import classify_gemini as _map_gemini_error
from .errors import (
    EngineError,
    ProviderOutputError,
    ProviderSafetyBlock,
    ProviderUnavailable,
)
from .openai_engine import _trim_conflicts, _trim_evidence
from .schemas import ClaimExtraction, ClaimReview, EvidenceAnalysis

logger = logging.getLogger("proofloop.engines.gemini")

SYSTEM_PROMPT = (
    "You are an independent evidence-analysis assistant inside ProofLoop AI. "
    "You never declare a claim true. Use only the supplied text and evidence. "
    "Never invent URLs, titles, publishers, dates or quotations. Return only the requested JSON."
)

EXTRACTION_PROMPT = """Split the text below into at most 8 atomic, independently checkable
factual claims. Preserve names, numbers, dates and meaning exactly. Do not add facts.
Use the same language as the text.

TEXT:
{text}
"""

ANALYSIS_PROMPT = """Assess the supplied evidence for the claim. For each item state whether it
supports, contradicts or is insufficient for the claim, its relevance, and why. Reference only
the exact source_url values supplied.

CLAIM:
{claim}

EVIDENCE:
{evidence}
"""

REVIEW_PROMPT = """Independently review whether the evidence supports the claim. Do not defer to
another model or to the deterministic verdict. The excerpts are the only admissible evidence.
Choose one recommended verdict from the schema, list concrete concerns, and explain your reasoning.

CLAIM:
{claim}

EVIDENCE:
{evidence}

DETERMINISTIC CONFLICTS:
{conflicts}
"""

SAFETY_REASONS = {"SAFETY", "BLOCKLIST", "PROHIBITED_CONTENT", "SPII", "RECITATION"}


class GeminiEngine:
    engine_id = "gemini"
    label = "Google Gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        live_enabled: bool,
        timeout: float = 20,
        max_retries: int = 2,
        max_input_chars: int = 12000,
        max_output_tokens: int = 1200,
        client: Any = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.live_enabled = live_enabled
        self.timeout = timeout
        self.max_retries = max_retries
        self.max_input_chars = max_input_chars
        self.max_output_tokens = max_output_tokens
        self._client = client

    def availability(self) -> dict[str, Any]:
        configured = bool(self.api_key and self.model)
        sdk = sdk_available("google.genai")
        available = configured and sdk and self.live_enabled
        if not sdk:
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
            capabilities=["claim_extraction", "evidence_analysis", "independent_review"],
            reason=reason,
        )

    def _require(self) -> None:
        if not self.live_enabled:
            raise ProviderUnavailable(
                "live_calls_disabled",
                "Live AI calls are disabled. Set PROOFLOOP_AI_LIVE_CALLS_ENABLED=true to opt in.",
            )
        if not self.api_key:
            raise ProviderUnavailable("missing_api_key", "GEMINI_API_KEY is not configured.")
        if not self.model:
            raise ProviderUnavailable("missing_model", "GEMINI_MODEL is not configured.")
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

    # ---------------------------------------------------------------- calls
    def _generate(
        self,
        *,
        prompt: str,
        schema: type,
        name: str,
    ) -> EngineCall:
        self._require()
        client = self._client_or_create()
        from google.genai import types

        correlation_id = new_correlation_id()
        started = time.monotonic()
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=self.max_output_tokens,
            response_mime_type="application/json",
            response_schema=schema,
        )
        payload = clamp(prompt, self.max_input_chars)

        def run() -> Any:
            try:
                return client.models.generate_content(
                    model=self.model, contents=payload, config=config
                )
            except Exception as exc:
                raise _map_gemini_error(exc) from exc

        response = call_with_retries(run, retries=self.max_retries)
        _raise_for_block(response)
        data = _parse(response, schema)
        usage = getattr(response, "usage_metadata", None)
        return EngineCall(
            data=data,
            usage=usage_payload(
                provider=self.engine_id,
                model=self.model,
                request_id=getattr(response, "response_id", None),
                correlation_id=correlation_id,
                started=started,
                input_tokens=getattr(usage, "prompt_token_count", None),
                output_tokens=getattr(usage, "candidates_token_count", None),
                total_tokens=getattr(usage, "total_token_count", None),
            ),
        )

    # ---------------------------------------------------------------- API
    def extract_claims(self, text: str) -> EngineCall:
        return self._generate(
            prompt=EXTRACTION_PROMPT.format(text=clamp(text, self.max_input_chars)),
            schema=ClaimExtraction,
            name="claim_extraction",
        )

    def analyze_evidence(
        self, claim_text: str, evidence: list[dict], allowed_urls: list[str]
    ) -> EngineCall:
        call = self._generate(
            prompt=ANALYSIS_PROMPT.format(
                claim=claim_text,
                evidence=json.dumps(_trim_evidence(evidence), ensure_ascii=False),
            ),
            schema=EvidenceAnalysis,
            name="evidence_analysis",
        )
        allowed = set(allowed_urls)
        call.data.notes = [note for note in call.data.notes if note.source_url in allowed]
        return call

    def review_claim(
        self, claim_text: str, evidence: list[dict], conflicts: list[dict]
    ) -> EngineCall:
        return self._generate(
            prompt=REVIEW_PROMPT.format(
                claim=claim_text,
                evidence=json.dumps(_trim_evidence(evidence), ensure_ascii=False),
                conflicts=json.dumps(_trim_conflicts(conflicts), ensure_ascii=False),
            ),
            schema=ClaimReview,
            name="claim_review",
        )

    def test(self) -> dict[str, Any]:
        call = self.extract_claims("The Eiffel Tower is 330 metres tall and was completed in 1889.")
        return {
            "ok": True,
            "detail": f"Structured response validated ({len(call.data.claims)} claim(s)).",
            "usage": call.usage,
        }


def _parse(response: Any, schema: type) -> Any:
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema):
        return parsed
    if isinstance(parsed, dict):
        try:
            return schema.model_validate(parsed)
        except (ValueError, TypeError) as exc:
            raise ProviderOutputError("Gemini returned output that failed validation.") from exc
    raw = getattr(response, "text", "") or ""
    if not raw.strip():
        raise ProviderOutputError("Gemini returned no text output.")
    raw = _strip_fence(raw)
    try:
        return schema.model_validate(json.loads(raw))
    except (ValueError, TypeError) as exc:
        raise ProviderOutputError("Gemini returned output that failed validation.") from exc


def _strip_fence(raw: str) -> str:
    value = raw.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        value = "\n".join(lines).strip()
    return value


def _raise_for_block(response: Any) -> None:
    feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(feedback, "block_reason", None) if feedback else None
    if block_reason:
        raise ProviderSafetyBlock(
            f"Gemini blocked the request ({_enum_value(block_reason)})."
        )
    for candidate in getattr(response, "candidates", None) or []:
        reason = _enum_value(getattr(candidate, "finish_reason", None))
        if reason in SAFETY_REASONS:
            raise ProviderSafetyBlock(f"Gemini stopped the response ({reason}).")


def _enum_value(value: Any) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value))
