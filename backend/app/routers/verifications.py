from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from .. import db, security
from ..engines import job_engines
from ..engines.errors import EngineError
from ..schemas import ClaimCreate, ClaimPatch, VerificationCreate
from ..services.graph import build_graph
from ..services.pipeline import ACTIVE_STATUSES, new_stages, run_pipeline
from ..services.report import build_report
from ..services.text import extract_dates, extract_entities, extract_numbers

router = APIRouter(prefix="/verifications", tags=["verifications"])


def _get_job(job_id: str, user_id: str) -> dict:
    job = db.get_verification(job_id, user_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Verification not found."},
        )
    return job


def _default_title(text: str, fallback: str) -> str:
    compact = " ".join(text.split())
    return (compact[:72] + ("…" if len(compact) > 72 else "")) if compact else fallback


def _refresh_report(job: dict) -> None:
    if job.get("report") is not None:
        job["report"] = build_report(job)


def _clear_claim_results(claim: dict) -> None:
    claim["evidence"] = []
    claim["verdict"] = "unverified"
    claim["verdict_basis"] = "Claim changed; run verification again to research this wording."


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def create_verification(
    payload: VerificationCreate,
    background: BackgroundTasks,
    user: dict = Depends(security.current_user),
):
    input_kind = "text"
    input_text: Optional[str] = payload.text
    input_url: Optional[str] = payload.url
    fallback_title = "Untitled verification"

    if payload.upload_id:
        upload = db.get_upload(payload.upload_id, user["id"])
        if not upload:
            raise HTTPException(
                status_code=404,
                detail={"code": "upload_not_found", "message": "Upload not found."},
            )
        input_kind = upload["kind"]
        if input_kind == "text":
            input_kind = "document"
        input_text = upload["extracted_text"]
        input_url = None
        fallback_title = upload["filename"]
    elif payload.url:
        input_kind = "url"

    title = (payload.title or "").strip() or _default_title(
        input_text or input_url or "", fallback_title
    )

    try:
        engines = job_engines(
            payload.engines.model_dump(exclude_none=True) if payload.engines else None
        )
    except EngineError as exc:
        raise HTTPException(
            status_code=422, detail={"code": exc.code, "message": exc.message}
        ) from exc

    job = {
        "id": db.new_id("ver"),
        "user_id": user["id"],
        "title": title,
        "input_kind": input_kind,
        "input_text": input_text,
        "input_url": input_url,
        "status": "queued",
        "error": None,
        "created_at": db.utcnow(),
        "updated_at": db.utcnow(),
        "engine": {"extraction": "deterministic", "research": "wikipedia"},
        "engines": engines,
        "ai_usage": [],
        "research_provenance": [],
        "stages": new_stages(),
        "claims": [],
        "sources": [],
        "contradictions": [],
        "report": None,
    }
    db.save_verification(job)
    background.add_task(run_pipeline, job["id"], user["id"])
    return {"id": job["id"], "status": job["status"], "title": job["title"]}


@router.get("")
def list_verifications(
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    user: dict = Depends(security.current_user),
):
    items, total = db.list_verifications(user["id"], limit=limit, offset=offset, status=status_filter)
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{job_id}")
def get_verification(job_id: str, user: dict = Depends(security.current_user)):
    job = _get_job(job_id, user["id"])
    for claim in job.get("claims", []):
        claim.pop("_candidates", None)
    return job


@router.post("/{job_id}/run", status_code=status.HTTP_202_ACCEPTED)
def rerun(
    job_id: str,
    background: BackgroundTasks,
    user: dict = Depends(security.current_user),
):
    job = _get_job(job_id, user["id"])
    if job["status"] in ACTIVE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail={"code": "already_running", "message": "This verification is already running."},
        )
    job["status"] = "queued"
    job["error"] = None
    db.update_verification(job)
    background.add_task(run_pipeline, job_id, user["id"])
    return {"id": job_id, "status": "queued"}


@router.post("/{job_id}/claims", status_code=201)
def add_claim(
    job_id: str,
    payload: ClaimCreate,
    user: dict = Depends(security.current_user),
):
    job = _get_job(job_id, user["id"])
    claim = {
        "id": db.new_id("clm"),
        "text": payload.text if payload.text.endswith((".", "!", "?")) else payload.text + ".",
        "original_span": payload.text,
        "category": "general",
        "entities": extract_entities(payload.text),
        "numbers": extract_numbers(payload.text),
        "dates": extract_dates(payload.text),
        "confidence": 1.0,
        "verdict": "unverified",
        "verdict_basis": "Manually added; run verification to research this claim.",
        "research_failed": False,
        "evidence": [],
        "manual": True,
    }
    job["claims"].append(claim)
    _refresh_report(job)
    db.update_verification(job)
    return claim


@router.patch("/{job_id}/claims/{claim_id}")
def patch_claim(
    job_id: str,
    claim_id: str,
    payload: ClaimPatch,
    user: dict = Depends(security.current_user),
):
    job = _get_job(job_id, user["id"])
    claim = next((item for item in job["claims"] if item["id"] == claim_id), None)
    if not claim:
        raise HTTPException(
            status_code=404, detail={"code": "claim_not_found", "message": "Claim not found."}
        )
    claim["text"] = payload.text if payload.text.endswith((".", "!", "?")) else payload.text + "."
    claim["entities"] = extract_entities(claim["text"])
    claim["numbers"] = extract_numbers(claim["text"])
    claim["dates"] = extract_dates(claim["text"])
    _clear_claim_results(claim)
    job["contradictions"] = [
        item for item in job["contradictions"] if item["claim_id"] != claim_id
    ]
    _refresh_report(job)
    db.update_verification(job)
    return claim


@router.delete("/{job_id}/claims/{claim_id}")
def delete_claim(job_id: str, claim_id: str, user: dict = Depends(security.current_user)):
    job = _get_job(job_id, user["id"])
    before = len(job["claims"])
    job["claims"] = [item for item in job["claims"] if item["id"] != claim_id]
    if len(job["claims"]) == before:
        raise HTTPException(
            status_code=404, detail={"code": "claim_not_found", "message": "Claim not found."}
        )
    job["contradictions"] = [
        item for item in job["contradictions"] if item["claim_id"] != claim_id
    ]
    _refresh_report(job)
    db.update_verification(job)
    return {"ok": True, "claims": len(job["claims"])}


@router.get("/{job_id}/graph")
def get_graph(job_id: str, user: dict = Depends(security.current_user)):
    return build_graph(_get_job(job_id, user["id"]))


@router.get("/{job_id}/contradictions")
def get_contradictions(job_id: str, user: dict = Depends(security.current_user)):
    job = _get_job(job_id, user["id"])
    return {
        "contradictions": job.get("contradictions", []),
        "claims": [{"id": claim["id"], "text": claim["text"]} for claim in job.get("claims", [])],
    }


@router.get("/{job_id}/report")
def get_report(job_id: str, user: dict = Depends(security.current_user)):
    job = _get_job(job_id, user["id"])
    report = job.get("report") or build_report(job)
    return report
