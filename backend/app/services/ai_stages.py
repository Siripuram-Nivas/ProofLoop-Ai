from __future__ import annotations

import logging
from typing import Any

from ..engines import registry, router
from ..engines.errors import EngineError

logger = logging.getLogger("proofloop.ai_stages")
MAX_CLAIMS = 8


def apply_ai_stages(job: dict) -> None:
    """Attach recommendations from configured engines without changing deterministic verdicts."""
    config = job.get("engines") or registry.job_engines(None)
    job["ai_usage"] = job.get("ai_usage") or []
    job["ai"] = {
        "availability": registry.availability(),
        "notices": list(job.pop("ai_notices", [])),
        "events": [],
        "provider": None,
        "analysis": {"engine": config.get("analysis") or None, "claims_analyzed": 0},
        "review": {"engine": config.get("review") or None, "claims_reviewed": 0, "agreements": 0},
        "second_review": {
            "engine": config.get("second_review") or None,
            "claims_reviewed": 0,
            "agreements": 0,
        },
    }
    claims = job.get("claims", [])[:MAX_CLAIMS]
    analysis_name = config.get("analysis") or ""
    review_name = config.get("review") or ""
    second_name = config.get("second_review") or ""
    if second_name and second_name == review_name:
        job["ai"]["second_review"]["skipped"] = "same_as_review_engine"
        second_name = ""

    broken: set[str] = set()
    for claim in claims:
        evidence = claim.get("evidence", [])
        allowed_urls = [item.get("source_url") for item in evidence if item.get("source_url")]
        conflicts = [
            item for item in job.get("contradictions", []) if item.get("claim_id") == claim["id"]
        ]

        if analysis_name and analysis_name not in broken:
            try:
                routed = _routed(
                    job,
                    "analysis",
                    "analyze_evidence",
                    analysis_name,
                    claim["text"],
                    evidence,
                    allowed_urls,
                )
                claim["ai_analysis"] = {
                    "engine": routed.engine,
                    "notes": [note.model_dump() for note in routed.call.data.notes],
                }
                _record(job, routed.call.usage)
                job["ai"]["analysis"]["provider"] = routed.engine
                job["ai"]["analysis"]["claims_analyzed"] += 1
            except EngineError as exc:
                _note_failure(job["ai"]["analysis"], exc)
                broken.add(analysis_name)
                logger.warning("analysis engine %s failed: %s", analysis_name, exc.code)

        if review_name and review_name not in broken:
            review = _review(job, review_name, claim, evidence, conflicts, "independent_review")
            if review is not None:
                job["ai"]["review"]["claims_reviewed"] += 1
                job["ai"]["review"]["agreements"] += 1 if review["agrees_with_deterministic"] else 0
            elif job["ai"]["review"].get("error"):
                broken.add(review_name)

        if second_name and second_name not in broken:
            review = _review(job, second_name, claim, evidence, conflicts, "second_review")
            if review is not None:
                job["ai"]["second_review"]["claims_reviewed"] += 1
                job["ai"]["second_review"]["agreements"] += (
                    1 if review["agrees_with_deterministic"] else 0
                )
            elif job["ai"]["second_review"].get("error"):
                broken.add(second_name)

    job["ai_usage_total"] = {
        "requests": len(job["ai_usage"]),
        "total_tokens": sum(
            int(item.get("total_tokens") or 0) for item in job["ai_usage"]
        ),
    }


def _routed(job: dict, stage: str, method: str, preferred: str, *args: Any):
    routed = router.call(stage, method, preferred, *args)
    job["ai"]["events"].extend(
        {"stage": stage, **attempt} for attempt in routed.attempts
    )
    if routed.used_fallback:
        text = router.notice(routed.attempts)
        if text and text not in job["ai"]["notices"]:
            job["ai"]["notices"].append(text)
    job["ai"]["provider"] = routed.engine
    return routed


def _review(
    job: dict,
    name: str,
    claim: dict,
    evidence: list[dict],
    conflicts: list[dict],
    key: str,
) -> dict | None:
    section = "review" if key == "independent_review" else key
    try:
        routed = _routed(
            job, "review", "review_claim", name, claim["text"], evidence, conflicts
        )
    except EngineError as exc:
        _note_failure(job["ai"][section], exc)
        logger.warning("%s engine %s failed: %s", key, name, exc.code)
        return None
    data = routed.call.data
    review = {
        "engine": routed.engine,
        "recommended_verdict": data.recommended_verdict,
        "confidence": data.confidence,
        "concerns": data.concerns,
        "reasoning": data.reasoning,
        "agrees_with_deterministic": data.recommended_verdict == claim.get("verdict"),
    }
    job["ai"][section]["provider"] = routed.engine
    claim[key] = review
    _record(job, routed.call.usage)
    return review


def _record(job: dict, usage: dict) -> None:
    if usage:
        job.setdefault("ai_usage", []).append(usage)


def _note_failure(section: dict, exc: EngineError) -> None:
    section["error"] = {"code": exc.code, "message": exc.message}
    if exc.outcome_unknown:
        section["outcome_unknown"] = True
