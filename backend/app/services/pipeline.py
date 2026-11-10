from __future__ import annotations

import logging
from typing import Optional

from .. import db
from .evaluation import evaluate_claim
from .extraction import extract_claims
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
            claims, engine = extract_claims(job["input_text"])
            job["engine"] = {"extraction": engine, "research": "wikipedia"}
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
        _stage(job, "extract", "done", f"{len(job['claims'])} atomic claim(s)")
        _persist(job)

        job["status"] = "researching"
        _stage(job, "research", "active")
        _persist(job)
        sources: dict[str, dict] = {}
        failures = 0
        for claim in job["claims"]:
            claim["evidence"] = []
            claim["research_failed"] = False
            try:
                candidates = fetch_sources(claim["text"])
            except ResearchError as exc:
                failures += 1
                claim["research_failed"] = True
                logger.warning("research failed for %s: %s", claim["id"], exc)
                continue
            for candidate in candidates:
                key = str(candidate.get("page_id") or candidate["url"])
                source = sources.get(key)
                if source is None:
                    source = {
                        "id": db.new_id("src"),
                        "title": candidate["title"],
                        "url": candidate["url"],
                        "publisher": "Wikipedia, The Free Encyclopedia",
                        "source_type": "encyclopedia (tertiary)",
                        "published_at": None,
                        "updated_at": candidate.get("updated_at"),
                        "retrieved_at": candidate["retrieved_at"],
                        "quality": "medium",
                        "quality_note": (
                            "Community-edited tertiary source. Useful for orientation; verify "
                            "consequential claims against primary sources."
                        ),
                        "stale": candidate.get("stale", False),
                    }
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
            candidates = claim.pop("_candidates", [])
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

        _stage(job, "report", "active")
        job["report"] = build_report(job)
        job["status"] = "completed"
        _stage(job, "report", "done", "Evidence snapshot preserved in the report.")
        _persist(job)
    except Exception as exc:  # keep failures visible instead of leaving a job stuck
        logger.exception("pipeline crashed for %s", job_id)
        active = next((stage for stage in job["stages"] if stage["status"] == "active"), None)
        _fail(job, active["key"] if active else "ingest", f"Unexpected error: {exc.__class__.__name__}")


def _fail(job: dict, stage_key: str, message: str) -> None:
    job["status"] = "failed"
    job["error"] = message
    _stage(job, stage_key, "failed", message)
    for stage in job["stages"]:
        if stage["status"] == "active" and stage["key"] != stage_key:
            stage["status"] = "pending"
    _persist(job)
    logger.warning("verification %s failed at %s: %s", job["id"], stage_key, message)
