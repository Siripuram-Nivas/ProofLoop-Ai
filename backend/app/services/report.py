from __future__ import annotations

from datetime import datetime, timezone

VERDICT_LABELS = {
    "supported": "Supported",
    "contradicted": "Contradicted",
    "mixed": "Mixed evidence",
    "insufficient": "Insufficient evidence",
    "outdated": "Outdated evidence",
    "unverified": "Unverified",
    "inconclusive": "Inconclusive",
}


def build_report(job: dict) -> dict:
    claims = job.get("claims", [])
    sources = job.get("sources", [])
    contradictions = job.get("contradictions", [])
    verdicts = [claim.get("verdict") for claim in claims]
    summary = {
        "claims": len(claims),
        "supported": verdicts.count("supported"),
        "contradicted": verdicts.count("contradicted"),
        "mixed": verdicts.count("mixed"),
        "insufficient": verdicts.count("insufficient"),
        "outdated": verdicts.count("outdated"),
        "unverified": verdicts.count("unverified"),
        "inconclusive": verdicts.count("inconclusive"),
        "sources": len(sources),
        "conflicts": len(contradictions),
    }

    claim_findings = []
    for claim in claims:
        conflict_ids = {item["id"] for item in contradictions if item["claim_id"] == claim["id"]}
        claim_findings.append(
            {
                "id": claim["id"],
                "text": claim["text"],
                "category": claim.get("category"),
                "verdict": claim.get("verdict"),
                "verdict_label": VERDICT_LABELS.get(claim.get("verdict", ""), claim.get("verdict")),
                "verdict_basis": claim.get("verdict_basis"),
                "confidence": claim.get("confidence"),
                "confidence_kind": "extraction_confidence",
                "ai_analysis": claim.get("ai_analysis"),
                "independent_review": claim.get("independent_review"),
                "second_review": claim.get("second_review"),
                "evidence": [
                    {
                        "id": item["id"],
                        "relationship": item["relationship"],
                        "excerpt": item["excerpt"],
                        "explanation": item["explanation"],
                        "source_title": item["source_title"],
                        "source_url": item["source_url"],
                        "source_type": item.get("source_type"),
                        "quality": item.get("quality"),
                        "retrieved_at": item.get("retrieved_at"),
                        "source_updated_at": item.get("source_updated_at"),
                        "stale": item.get("stale", False),
                    }
                    for item in claim.get("evidence", [])
                ],
                "conflicts": [
                    {
                        "id": conflict["id"],
                        "kind": conflict["kind"],
                        "severity": conflict["severity"],
                        "summary": conflict["summary"],
                    }
                    for conflict in contradictions
                    if conflict["id"] in conflict_ids
                ],
            }
        )

    limitations = [
        "Research is performed against Wikipedia, a community-edited tertiary source. It is a "
        "starting point for investigation, not an authority. Primary sources should be checked "
        "before any consequential decision.",
        "Evidence is a snapshot retrieved at the timestamps shown. Articles can change after retrieval.",
        "Only the top excerpts per claim are evaluated. The absence of a contradiction in this report "
        "does not prove that no conflicting evidence exists.",
        "Verification compares numbers and dates deterministically (1% tolerance for numeric support, "
        "5% before a value is treated as a conflict). Ambiguous wording can reduce relevance scores.",
        "Claim extraction is limited to 8 atomic claims per run and is "
        + ("rule-based (deterministic)." if job.get("engine", {}).get("extraction") == "deterministic"
           else "assisted by an LLM, with every accepted claim checked against the original text."),
        "ProofLoop AI does not establish absolute truth. It reports what the retrieved evidence "
        "supports, contradicts, or leaves unresolved.",
    ]
    ai = job.get("ai") or {}
    reviewed = int((ai.get("review") or {}).get("claims_reviewed") or 0) + int(
        (ai.get("second_review") or {}).get("claims_reviewed") or 0
    )
    analyzed = int((ai.get("analysis") or {}).get("claims_analyzed") or 0)
    if reviewed or analyzed:
        limitations.append(
            "Model output is structured recommendation, not proof. Model agreement is not "
            "independent factual verification, and model confidence is never averaged into the "
            "verdict. Verdicts come from the persisted source excerpts and deterministic comparison."
        )
    if job.get("engine", {}).get("research") == "google_search":
        limitations.append(
            "Sources were discovered through Google Search grounding. Citation metadata is preserved, "
            "but only sources with a readable retrieved excerpt can support or contradict a claim."
        )

    if summary["inconclusive"] or summary["unverified"]:
        limitations.append(
            f"{summary['inconclusive'] + summary['unverified']} claim(s) have no usable evidence. "
            "Missing evidence is preserved as missing, not converted into a negative verdict."
        )
    if summary["conflicts"]:
        limitations.append(
            "Conflicting values are reported without automatically deciding which source is correct. "
            "Publication dates, definitions, and primary sources must be checked by the reader."
        )
    if any(item.get("stale") for claim in claims for item in claim.get("evidence", [])):
        limitations.append("At least one excerpt comes from a source last updated more than three years ago.")

    return {
        "verification_id": job["id"],
        "title": job["title"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "input_kind": job.get("input_kind"),
        "input_text": job.get("input_text"),
        "input_url": job.get("input_url"),
        "engine": job.get("engine", {}),
        "ai": ai,
        "ai_usage": job.get("ai_usage", []),
        "ai_usage_total": job.get("ai_usage_total"),
        "research_provenance": job.get("research_provenance", []),
        "summary": summary,
        "claims": claim_findings,
        "sources": sources,
        "contradictions": contradictions,
        "limitations": limitations,
        "methodology": [
            "Input parsed and preserved verbatim.",
            "Atomic claims extracted and independently researched.",
            "Real source excerpts retrieved with URL and timestamps.",
            "Relevance scored by content-term overlap; numbers and years compared deterministically.",
            "Verdicts aggregated conservatively; conflicts and missing evidence kept visible.",
        ],
        "disclaimer": (
            "This report is an evidence snapshot, not a truth certificate. Every conclusion is "
            "traceable to the listed sources; check them independently."
        ),
    }
