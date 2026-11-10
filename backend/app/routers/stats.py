from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import db, security

router = APIRouter(tags=["stats"])


@router.get("/stats")
def dashboard_stats(user: dict = Depends(security.current_user)):
    totals = db.stats(user["id"])
    recent, _ = db.list_verifications(user["id"], limit=6)
    conflicts = []
    latest_report = None
    for item in recent[:5]:
        job = db.get_verification(item["id"], user["id"])
        if not job:
            continue
        if latest_report is None and job.get("report"):
            latest_report = {
                "verification_id": job["id"],
                "title": job["title"],
                "generated_at": job["report"].get("generated_at"),
                "summary": job["report"].get("summary"),
            }
        for conflict in job.get("contradictions", [])[:3]:
            conflicts.append(
                {
                    "verification_id": job["id"],
                    "verification_title": job["title"],
                    "claim_id": conflict["claim_id"],
                    "kind": conflict["kind"],
                    "severity": conflict["severity"],
                    "summary": conflict["summary"],
                }
            )
    return {
        "totals": totals,
        "recent": recent,
        "conflicts": conflicts[:6],
        "latest_report": latest_report,
    }
