from __future__ import annotations

import math
from typing import Optional

from ..db import new_id
from .text import number_mentions, overlap_score, year_mentions

SUPPORT_TOLERANCE = 0.01
NEAR_TOLERANCE = 0.05


def _fmt(value: float) -> str:
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.4g}"


def _context_match(claim_items: list[dict], evidence_items: list[dict]) -> list[tuple[dict, dict]]:
    matched: list[tuple[dict, dict]] = []
    for claim_item in claim_items:
        candidates = [item for item in evidence_items if claim_item["context"] & item["context"]]
        if not candidates and len(claim_items) == 1 and len(evidence_items) == 1:
            candidates = evidence_items
        if candidates:
            best = min(candidates, key=lambda item: abs(item["value"] - claim_item["value"]) / max(abs(claim_item["value"]), 1))
            matched.append((claim_item, best))
    return matched


def _number_analysis(claim_text: str, excerpt: str) -> dict:
    claim_items = number_mentions(claim_text)
    evidence_items = number_mentions(excerpt)
    pairs = []
    for claim_item, evidence_item in _context_match(claim_items, evidence_items):
        denominator = max(abs(claim_item["value"]), 1.0)
        diff = abs(claim_item["value"] - evidence_item["value"]) / denominator
        if diff <= SUPPORT_TOLERANCE:
            kind = "match"
        elif diff <= NEAR_TOLERANCE:
            kind = "near"
        else:
            kind = "mismatch"
        pairs.append(
            {
                "claim_value": claim_item["value"],
                "evidence_value": evidence_item["value"],
                "relative_diff": round(diff, 6),
                "kind": kind,
            }
        )
    return {"pairs": pairs}


def _year_analysis(claim_text: str, excerpt: str) -> dict:
    claim_items = year_mentions(claim_text)
    evidence_items = year_mentions(excerpt)
    pairs = []
    for claim_item, evidence_item in _context_match(claim_items, evidence_items):
        if claim_item["value"] == evidence_item["value"]:
            kind = "match"
        elif abs(claim_item["value"] - evidence_item["value"]) <= 1:
            kind = "near"
        else:
            kind = "mismatch"
        pairs.append(
            {
                "claim_value": claim_item["value"],
                "evidence_value": evidence_item["value"],
                "kind": kind,
            }
        )
    return {"pairs": pairs}


def _format_value(value: float) -> str:
    return _fmt(value)


def evaluate_claim(claim: dict, candidates: list[dict], research_failed: bool) -> tuple[list[dict], str, str]:
    evidence: list[dict] = []
    for candidate in candidates:
        excerpt = candidate["excerpt"]
        score, shared = overlap_score(claim["text"], excerpt)
        if len(shared) < 2 or score < 0.3:
            continue
        numbers = _number_analysis(claim["text"], excerpt)
        years = _year_analysis(claim["text"], excerpt)
        numeric_match = [p for p in numbers["pairs"] if p["kind"] in ("match", "near")]
        numeric_mismatch = [p for p in numbers["pairs"] if p["kind"] == "mismatch"]
        year_match = [p for p in years["pairs"] if p["kind"] in ("match", "near")]
        year_mismatch = [p for p in years["pairs"] if p["kind"] == "mismatch"]

        if numeric_mismatch:
            relationship = "contradicts"
            match_kind = "numeric_mismatch"
            pair = numeric_mismatch[0]
            explanation = (
                f"The excerpt reports {_format_value(pair['evidence_value'])} where the claim states "
                f"{_format_value(pair['claim_value'])} ({pair['relative_diff'] * 100:.1f}% difference)."
            )
        elif year_mismatch:
            relationship = "contradicts"
            match_kind = "date_mismatch"
            pair = year_mismatch[0]
            explanation = (
                f"The excerpt refers to {int(pair['evidence_value'])} while the claim states "
                f"{int(pair['claim_value'])}."
            )
        elif numeric_match:
            relationship = "supports"
            pair = numeric_match[0]
            match_kind = "numeric"
            explanation = (
                f"The excerpt reports {_format_value(pair['evidence_value'])}, consistent with the claim's "
                f"{_format_value(pair['claim_value'])} (within {max(pair['relative_diff'] * 100, 0.01):.2f}%)."
            )
        elif year_match:
            relationship = "supports"
            match_kind = "date"
            explanation = f"The excerpt confirms the year {int(year_match[0]['evidence_value'])}."
        elif score >= 0.6 and len(shared) >= 3:
            relationship = "supports"
            match_kind = "textual"
            explanation = (
                "The excerpt covers the claim's key terms but contains no comparable number or date. "
                "This is qualitative support only."
            )
        else:
            relationship = "insufficient"
            match_kind = "weak_overlap"
            explanation = (
                "The excerpt shares some terms with the claim but is too weak or ambiguous to count as "
                "supporting evidence."
            )

        stale = bool(candidate.get("stale"))
        evidence.append(
            {
                "id": new_id("ev"),
                "claim_id": claim["id"],
                "source_id": candidate["source_id"],
                "source_title": candidate["title"],
                "source_url": candidate["url"],
                "source_type": candidate["source_type"],
                "quality": candidate["quality"],
                "excerpt": excerpt,
                "relationship": relationship,
                "match_kind": match_kind,
                "explanation": explanation,
                "matched_terms": shared[:12],
                "relevance": round(score, 2),
                "numbers": numbers["pairs"],
                "years": years["pairs"],
                "retrieved_at": candidate["retrieved_at"],
                "source_updated_at": candidate.get("updated_at"),
                "stale": stale,
            }
        )

    supports = [item for item in evidence if item["relationship"] == "supports"]
    contradicts = [item for item in evidence if item["relationship"] == "contradicts"]
    strong_support = [item for item in supports if item["match_kind"] in ("numeric", "date")]
    all_support_stale = bool(supports) and all(item["stale"] for item in supports)

    if contradicts and supports:
        verdict = "mixed"
        basis = f"{len(supports)} supporting and {len(contradicts)} contradicting excerpts were found."
    elif contradicts:
        verdict = "contradicted"
        basis = f"{len(contradicts)} excerpt(s) conflict with the claim; no supporting excerpt was found."
    elif strong_support or len(supports) >= 2:
        verdict = "supported"
        basis = (
            f"{len(strong_support)} numeric/date match(es) and {len(supports)} supporting excerpt(s), "
            "with no contradiction found in the retrieved evidence."
        )
    elif supports:
        verdict = "insufficient"
        basis = "One qualitative excerpt supports the claim, but it provides no independently checkable figure or date."
    elif evidence:
        verdict = "insufficient"
        basis = "Related excerpts were retrieved but none met the threshold for supporting or contradicting the claim."
    else:
        verdict = "inconclusive" if research_failed else "unverified"
        basis = (
            "Research did not complete, so no evidence could be evaluated."
            if research_failed
            else "No relevant source excerpt was retrieved. This is not evidence that the claim is false."
        )

    if verdict == "supported" and all_support_stale:
        verdict = "outdated"
        basis = "All supporting excerpts come from sources older than three years."

    return evidence, verdict, basis
