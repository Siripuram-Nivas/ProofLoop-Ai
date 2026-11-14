from __future__ import annotations

import logging
import re
from typing import Optional

from .. import db
from ..engines import registry, router
from ..engines.errors import EngineError
from .ai_stages import apply_ai_stages
from .evaluation import evaluate_claim
from .extraction import build_claim, extract_claims
from .ingest import IngestError, fetch_url
from .report import build_report
from .research import ResearchError, fetch_sources
from .contradictions import detect_contradictions

logger = logging.getLogger("proofloop.pipeline")

STAGE_DEFS = [
    ("ingest", "Input received"),
    ("extract", "Atomic claims extracted"),
    ("research", "Sources researched"),
    ("evaluate", "Evidence evaluated"),
    ("conflicts", "Conflicts checked"),
    ("report", "Proof report generated"),
]
ACTIVE_STATUSES = {"queued", "extracting", "researching", "evaluating"}


def new_stages() -> list[dict]:
    return [
        {"key": key, "label": label, "status": "pending", "detail": "", "at": None}
        for key, label in STAGE_DEFS
    ]


def _stage(job: dict, key: str, status: str, detail: str = "") -> None:
    for stage in job["stages"]:
        if stage["key"] == key:
            stage["status"] = status
            stage["detail"] = detail
            stage["at"] = db.utcnow() if status in ("done", "failed", "partial") else stage["at"]
            return


def _persist(job: dict) -> None:
    db.update_verification(job)


def run_pipeline(job_id: str, user_id: str) -> None:
    job = db.get_verification(job_id, user_id)
    if not job:
        return
    job["stages"] = new_stages()
    job["error"] = None
    job["status"] = "extracting"
    job["claims"] = job.get("claims") or []
    job["sources"] = []
    job["contradictions"] = []
    job["report"] = None
    job["engines"] = job.get("engines") or registry.job_engines(None)
    job["ai_usage"] = []
    job["research_provenance"] = []
    config = job["engines"]
    _stage(job, "ingest", "active")
    _persist(job)

    try:
        if job.get("input_url") and not job.get("input_text"):
            try:
                job["input_text"] = fetch_url(job["input_url"])
            except IngestError as exc:
                _fail(job, "ingest", f"Could not read the URL: {exc}")
                return
            _persist(job)
        if not job.get("input_text"):
            _fail(job, "ingest", "No readable input text was available.")
            return
        _stage(job, "ingest", "done", f"{len(job['input_text'])} characters preserved")

        _stage(job, "extract", "active")
        if not job["claims"]:
            choice = config.get("claim_extraction", "deterministic")
            if choice in {"openai", "gemini"}:
                claims, engine = _engine_claims(job, choice)
                if claims is None:
                    return
            else:
                claims, engine = extract_claims(job["input_text"])
            job["engine"] = {
                "extraction": engine,
                "research": config.get("research", "wikipedia"),
                "analysis": config.get("analysis") or None,
                "review": config.get("review") or None,
                "second_review": config.get("second_review") or None,
            }
            for claim in claims:
                claim["id"] = db.new_id("clm")
                claim["evidence"] = []
                claim["verdict"] = "unverified"
                claim["verdict_basis"] = "Not evaluated yet."
                claim["research_failed"] = False
            job["claims"] = claims
        if not job["claims"]:
            _fail(job, "extract", "No independently verifiable claims could be extracted.")
            return
        _stage(job, "extract", "done", f"{len(job['claims'])} atomic claim(s) via {job['engine']['extraction']}")
        _persist(job)

        job["status"] = "researching"
        _stage(job, "research", "active")
        _persist(job)
        research_choice = config.get("research", "wikipedia")
        sources: dict[str, dict] = {}
        failures = 0
        readable = 0
        for claim in job["claims"]:
            claim["evidence"] = []
            claim["research_failed"] = False
            try:
                if research_choice == "google_search":
                    candidates = _search_candidates(job, claim)
                else:
                    candidates = fetch_sources(claim["text"])
            except (ResearchError, EngineError) as exc:
                failures += 1
                claim["research_failed"] = True
                if research_choice == "google_search":
                    # Grounding is a Gemini capability; no text model may stand in for it.
                    job["research_provenance"].append(
                        {
                            "claim_id": claim["id"],
                            "engine": "google_search",
                            "unavailable": True,
                            "code": getattr(exc, "code", "research_failed"),
                            "message": str(exc),
                        }
                    )
                logger.warning("research failed for %s: %s", claim["id"], exc)
                continue
            readable += sum(1 for candidate in candidates if candidate.get("excerpt"))
            for candidate in candidates:
                key = str(candidate.get("page_id") or candidate["url"])
                source = sources.get(key)
                if source is None:
                    source = _source_record(candidate, research_choice)
                    sources[key] = source
                candidate["source_id"] = source["id"]
                candidate["source_type"] = source["source_type"]
                candidate["quality"] = source["quality"]
            claim["_candidates"] = candidates
        job["sources"] = list(sources.values())
        if failures == len(job["claims"]):
            _stage(job, "research", "failed", "Research provider unavailable for all claims.")
        elif failures:
            _stage(job, "research", "partial", f"{failures} of {len(job['claims'])} claim(s) could not be researched.")
        elif research_choice == "google_search" and not readable:
            _stage(
                job,
                "research",
                "partial",
                f"{len(job['sources'])} source(s) discovered, no readable excerpt retrieved.",
            )
        else:
            _stage(
                job,
                "research",
                "done",
                f"{len(job['sources'])} source(s) retrieved for {len(job['claims'])} claim(s)",
            )
        _persist(job)

        job["status"] = "evaluating"
        _stage(job, "evaluate", "active")
        _persist(job)
        for claim in job["claims"]:
            candidates = [
                item for item in claim.pop("_candidates", []) if item.get("excerpt")
            ]
            evidence, verdict, basis = evaluate_claim(
                claim, candidates, claim.get("research_failed", False)
            )
            claim["evidence"] = evidence
            claim["verdict"] = verdict
            claim["verdict_basis"] = basis
        _stage(job, "evaluate", "done", "Evidence classified deterministically.")
        _persist(job)

        _stage(job, "conflicts", "active")
        job["contradictions"] = detect_contradictions(job["claims"])
        _stage(
            job,
            "conflicts",
            "done",
            f"{len(job['contradictions'])} conflict(s) recorded",
        )

        try:
            apply_ai_stages(job)
        except Exception:  # AI recommendations must never break the deterministic pipeline
            logger.exception("AI stage failed for %s", job_id)
            job.setdefault("ai", {})["error"] = "AI analysis failed unexpectedly."
        _persist(job)

        _stage(job, "report", "active")
        job["report"] = build_report(job)
        job["status"] = "completed"
        _stage(job, "report", "done", "Evidence snapshot preserved in the report.")
        _persist(job)
    except Exception as exc:  # keep failures visible instead of leaving a job stuck
        logger.exception("pipeline crashed for %s", job_id)
        active = next((stage for stage in job["stages"] if stage["status"] == "active"), None)
        _fail(job, active["key"] if active else "ingest", f"Unexpected error: {exc.__class__.__name__}")


def _engine_claims(job: dict, choice: str) -> tuple[Optional[list[dict]], str]:
    try:
        routed = router.call("extraction", "extract_claims", choice, job["input_text"])
    except EngineError as exc:
        _fail(job, "extract", f"Claim extraction failed: {exc.message}")
        return None, choice
    if routed.used_fallback:
        text = router.notice(routed.attempts)
        if text:
            job.setdefault("ai_notices", []).append(text)
        job.setdefault("ai_extraction_attempts", []).extend(routed.attempts)
    call = routed.call
    _record_usage(job, call.usage)
    source_norm = _normalise(job["input_text"])
    claims: list[dict] = []
    for item in call.data.claims[:8]:
        if _normalise(item.text) not in source_norm:
            continue
        claims.append(build_claim(item.text, category=item.category, confidence=item.confidence))
    if not claims:
        _fail(
            job,
            "extract",
            f"{routed.engine} returned no claims grounded in the original text.",
        )
        return None, routed.engine
    return claims, routed.engine


def _search_candidates(job: dict, claim: dict) -> list[dict]:
    discovery = registry.resolve("google_search").search(claim["text"])
    _record_usage(job, discovery.usage)
    job["research_provenance"].append(
        {
            "claim_id": claim["id"],
            "engine": "google_search",
            "queries": discovery.queries,
            "grounding": discovery.grounding,
            "sources_discovered": len(discovery.sources),
            "invalid_sources": discovery.invalid_sources,
        }
    )
    candidates = []
    for source in discovery.sources:
        candidates.append(
            {
                "page_id": None,
                "title": source.title or source.publisher or source.url,
                "url": source.url,
                "excerpt": source.excerpt,
                "publisher": source.publisher,
                "source_type": "web page (search-discovered)",
                "quality": "unknown",
                "quality_note": (
                    "Discovered through Google Search grounding. Reliability is not assessed "
                    "automatically; check the publisher and publication date."
                ),
                "retrieved_at": source.retrieved_at,
                "updated_at": None,
                "stale": False,
                "locator": source.locator,
                "accessible": source.accessible,
                "note": source.note,
                "provenance": source.provenance,
            }
        )
    return candidates


def _source_record(candidate: dict, research_choice: str) -> dict:
    wikipedia = research_choice == "wikipedia"
    return {
        "id": db.new_id("src"),
        "title": candidate.get("title") or candidate["url"],
        "url": candidate["url"],
        "publisher": candidate.get("publisher")
        or ("Wikipedia, The Free Encyclopedia" if wikipedia else "Unknown"),
        "source_type": candidate.get("source_type")
        or ("encyclopedia (tertiary)" if wikipedia else "web page"),
        "published_at": candidate.get("published_at"),
        "updated_at": candidate.get("updated_at"),
        "retrieved_at": candidate["retrieved_at"],
        "quality": candidate.get("quality") or ("medium" if wikipedia else "unknown"),
        "quality_note": candidate.get("quality_note")
        or (
            "Community-edited tertiary source. Useful for orientation; verify consequential "
            "claims against primary sources."
            if wikipedia
            else "Reliability not assessed automatically."
        ),
        "stale": candidate.get("stale", False),
        "accessible": candidate.get("accessible", True),
        "locator": candidate.get("locator"),
        "provenance": {
            "discovery": research_choice,
            **(candidate.get("provenance") or {}),
        },
    }


def _record_usage(job: dict, usage: dict) -> None:
    if usage:
        job.setdefault("ai_usage", []).append(usage)


def _normalise(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _fail(job: dict, stage_key: str, message: str) -> None:
    job["status"] = "failed"
    job["error"] = message
    _stage(job, stage_key, "failed", message)
    for stage in job["stages"]:
        if stage["status"] == "active" and stage["key"] != stage_key:
            stage["status"] = "pending"
    _persist(job)
    logger.warning("verification %s failed at %s: %s", job["id"], stage_key, message)
