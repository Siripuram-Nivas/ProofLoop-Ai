from __future__ import annotations

import json
import logging
import time
from typing import Any, Optional

from .base import (
    EngineCall,
    availability,
    call_with_retries,
    clamp,
    new_correlation_id,
    sdk_available,
    usage_payload,
)
from .classify import classify_openai as _map_openai_error
from .errors import (
    EngineError,
    ProviderOutputError,
    ProviderRefusal,
    ProviderUnavailable,
)
from .schemas import ClaimExtraction, ClaimReview, EvidenceAnalysis

logger = logging.getLogger("proofloop.engines.openai")

SYSTEM_PROMPT = (
    "You are an evidence-analysis assistant inside ProofLoop AI. You never state that a claim "
    "is true. Return only the requested JSON structure. Use only facts present in the supplied "
    "text or evidence. Never invent URLs, titles, publishers, dates or quotations."
)

EXTRACTION_PROMPT = """Split the text below into at most 8 atomic, independently checkable
factual claims. Preserve names, numbers, dates and meaning exactly. Do not add facts that are
not in the text. Use the same language as the text.

TEXT:
{text}
"""

ANALYSIS_PROMPT = """Assess the supplied evidence for the claim. For each evidence item, say
whether it supports, contradicts or is insufficient for the claim, how relevant it is, and why.
Reference only the exact source_url values supplied. Do not invent sources.

CLAIM:
{claim}

EVIDENCE:
{evidence}
"""

REVIEW_PROMPT = """Independently review how well the evidence supports the claim. Do not defer to
another model. Choose one recommended verdict from the schema, list concrete concerns, and explain
your reasoning. The evidence excerpts are the only admissible evidence.

CLAIM:
{claim}

EVIDENCE:
{evidence}

DETERMINISTIC CONFLICTS:
{conflicts}
"""


class OpenAIEngine:
    engine_id = "openai"
    label = "OpenAI"

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

    # ---------------------------------------------------------------- state
    def availability(self) -> dict[str, Any]:
        configured = bool(self.api_key and self.model)
        sdk = sdk_available("openai")
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
            raise ProviderUnavailable("missing_api_key", "OPENAI_API_KEY is not configured.")
        if not self.model:
            raise ProviderUnavailable("missing_model", "OPENAI_MODEL is not configured.")
        if not sdk_available("openai"):
            raise ProviderUnavailable("sdk_missing", "The openai SDK is not installed.")

    def _client_or_create(self) -> Any:
        if self._client is not None:
            return self._client
        self._require()
        import openai

        self._client = openai.OpenAI(
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=0,
        )
        return self._client

    # ---------------------------------------------------------------- calls
    def _structured(
        self,
        *,
        prompt: str,
        schema: type,
        name: str,
    ) -> EngineCall:
        self._require()
        client = self._client_or_create()
        payload = clamp(prompt, self.max_input_chars)
        correlation_id = new_correlation_id()
        started = time.monotonic()

        def run() -> Any:
            try:
                return client.responses.create(
                    model=self.model,
                    instructions=SYSTEM_PROMPT,
                    input=payload,
                    text={
                        "format": {
                            "type": "json_schema",
                            "name": name,
                            "schema": strict_schema(schema),
                            "strict": True,
                        }
                    },
                    max_output_tokens=self.max_output_tokens,
                    # temperature omitted: some models reject it outright.
                    store=False,
                )
            except Exception as exc:
                raise _map_openai_error(exc) from exc

        try:
            response = call_with_retries(run, retries=self.max_retries)
        except EngineError:
            raise

        _raise_for_refusal(response)
        if getattr(response, "status", "") == "incomplete":
            reason = getattr(getattr(response, "incomplete_details", None), "reason", None)
            raise ProviderOutputError(
                f"OpenAI returned an incomplete response ({reason or 'unknown reason'})."
            )
        raw = getattr(response, "output_text", "") or ""
        if not raw.strip():
            raise ProviderOutputError("OpenAI returned no text output.")

        try:
            data = schema.model_validate(json.loads(raw))
        except (ValueError, TypeError) as exc:
            raise ProviderOutputError("OpenAI returned output that failed validation.") from exc

        usage = getattr(response, "usage", None)
        return EngineCall(
            data=data,
            usage=usage_payload(
                provider=self.engine_id,
                model=self.model,
                request_id=getattr(response, "id", None),
                correlation_id=correlation_id,
                started=started,
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                total_tokens=getattr(usage, "total_tokens", None),
            ),
        )

    # ---------------------------------------------------------------- API
    def extract_claims(self, text: str) -> EngineCall:
        return self._structured(
            prompt=EXTRACTION_PROMPT.format(text=clamp(text, self.max_input_chars)),
            schema=ClaimExtraction,
            name="claim_extraction",
        )

    def analyze_evidence(
        self, claim_text: str, evidence: list[dict], allowed_urls: list[str]
    ) -> EngineCall:
        call = self._structured(
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
        return self._structured(
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


def strict_schema(model: type) -> dict:
    """Pydantic schema in the shape OpenAI Structured Outputs requires.

    Strict mode rejects defaults and optional properties, and every object must be
    closed with additionalProperties: false. Pydantic emits none of that by default.
    """
    return _strict_node(model.model_json_schema())


def _strict_node(node: Any) -> Any:
    if isinstance(node, list):
        return [_strict_node(item) for item in node]
    if not isinstance(node, dict):
        return node
    out = {key: _strict_node(value) for key, value in node.items() if key != "default"}
    if "properties" in out:
        out["additionalProperties"] = False
        out["required"] = list(out["properties"])
    return out


def _trim_evidence(evidence: list[dict]) -> list[dict]:
    trimmed = []
    for item in evidence[:8]:
        trimmed.append(
            {
                "source_url": item.get("source_url"),
                "source_title": item.get("source_title"),
                "excerpt": clamp(str(item.get("excerpt") or ""), 900),
                "deterministic_relationship": item.get("relationship"),
            }
        )
    return trimmed


def _trim_conflicts(conflicts: list[dict]) -> list[dict]:
    return [
        {
            "kind": item.get("kind"),
            "severity": item.get("severity"),
            "summary": clamp(str(item.get("summary") or ""), 400),
        }
        for item in conflicts[:6]
    ]


def _raise_for_refusal(response: Any) -> None:
    for item in getattr(response, "output", None) or []:
        if getattr(item, "type", "") == "refusal":
            raise ProviderRefusal(_refusal_text(item))
        for part in getattr(item, "content", None) or []:
            if getattr(part, "type", "") == "refusal":
                raise ProviderRefusal(_refusal_text(part))


def _refusal_text(item: Any) -> str:
    text = getattr(item, "refusal", None) or getattr(item, "text", None)
    return clamp(str(text or "The request was refused by OpenAI."), 400)
